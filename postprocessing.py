"""
Post-processing:
- EdgeFramebuffer: zapisywane w pamięci normalne + glebokosc, do ktorych
  renderujemy scene w Pass 1, zamiast bezpośrednio na ekran.
- FullscreenQuad: płótno pokrywające caly ekran, na ktorym w Pass 3
  wykonuje się shader Sobela, czytając dane zapisane przez EdgeFramebuffer.

"""
import ctypes
import numpy as np
from OpenGL.GL import *


class EdgeFramebuffer:
    """Framebuffer offscreen do pass geometrii.

    Renderujemy scenę nie na ekran, tylko do dwoch tekstur:
      - normal_tex: normalna kazdego fragmentu w przestrzeni widoku
        (view-space), zapisana wprost jako kolor.
      - depth_tex: bufor glebokosci OpenGL, ale podpiety jako
        tekstura do ODCZYTU.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.fbo = None
        self.normal_tex = None
        self.depth_tex = None
        self._create(width, height)

    # Tworzy framebuffer i tekstury do wykrywania krawędzi
    def _create(self, width, height):
        self.width, self.height = width, height
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

        # --- tekstura normalnych ---
        self.normal_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.normal_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB16F, width, height, 0,
                     GL_RGB, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                GL_TEXTURE_2D, self.normal_tex, 0)

        # --- tekstura glebokosci ---
        self.depth_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.depth_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, width, height, 0,
                     GL_DEPTH_COMPONENT, GL_FLOAT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                                GL_TEXTURE_2D, self.depth_tex, 0)

        glDrawBuffers(1, [GL_COLOR_ATTACHMENT0])

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError(f"Framebuffer niekompletny (status={status})")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    # Odtwarza framebuffer po zmianie rozmiaru okna
    def resize(self, width, height):
        self.delete()
        self._create(width, height)

    # Ustawia framebuffer jako miejsce dla renderowania
    def bind_for_writing(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.width, self.height)

    # Przywraca renderowanie bezpośrednio na ekran
    def unbind(self, screen_w, screen_h):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, screen_w, screen_h)

    # Wysyła tekstury normalnych i głębokości shaderowi
    def bind_textures(self, normal_unit=0, depth_unit=1):
        glActiveTexture(GL_TEXTURE0 + normal_unit)
        glBindTexture(GL_TEXTURE_2D, self.normal_tex)
        glActiveTexture(GL_TEXTURE0 + depth_unit)
        glBindTexture(GL_TEXTURE_2D, self.depth_tex)

    # Usuwa zasoby framebuffera
    def delete(self):
        if self.fbo is not None:
            glDeleteFramebuffers(1, [self.fbo])
        if self.normal_tex is not None:
            glDeleteTextures([self.normal_tex])
        if self.depth_tex is not None:
            glDeleteTextures([self.depth_tex])


class FullscreenQuad:
    """Pelnoekranowy prostokat uzywany jako "plotno" do rysowania efektu post-processingu (Sobel)"""

    def __init__(self):
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 1.0,
        ], dtype=np.float32)
        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        stride = 4 * 4  # 4 floaty * 4 bajty
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(8))
        glEnableVertexAttribArray(1)

        ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        glBindVertexArray(0)

    # Rysuje pełnoekranowy prostokąt
    def draw(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)