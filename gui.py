"""
Nakladka 2D GUI na scene 3D 

pygame_gui to biblioteka do rysowania na zwykłej pygame.Surface
Okno jest jednak w trybie OPENGL gdzie nie ma normalnej powierzchni 2D do rysowania; 
pygame_gui nie wie nic o OpenGL. 

Co klatkę:
1) tworzymy przezroczystą powierzchnię,
2) mowimy pygame_gui aby narysowała na niej swoje elementy (przyciski, suwaki)
3) wysyłamy tą powierzchnię jako teksturę do OpenGL,
4) rysuje się przezroczysty prostokąt z GUI na wierzchu sceny 3D.
"""
import pygame
import pygame_gui
from OpenGL.GL import *


class UIOverlay:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.manager = pygame_gui.UIManager((width, height))

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, None)
        glBindTexture(GL_TEXTURE_2D, 0)

    # Dopasowuje GUI i teksturę do nowego rozmiaru okna
    def resize(self, width, height):
        self.width, self.height = width, height
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.manager.set_window_resolution((width, height))
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, None)
        glBindTexture(GL_TEXTURE_2D, 0)

    # Przekazuje zdarzenie do systemu GUI
    def process_event(self, event):
        self.manager.process_events(event)

    # Aktualizuje stan elementów interfejsu
    def update(self, dt):
        self.manager.update(dt)

    # Rysuje GUI jako teksturę OpenGL na scenie
    def draw(self):
        glActiveTexture(GL_TEXTURE0)

        #czyszczenie powierzchni i rysowanie przyciskow
        self.surface.fill((0, 0, 0, 0))
        self.manager.draw_ui(self.surface)
        #dla opengl przekazanie surface surowo - bajtowo
        data = pygame.image.tostring(self.surface, "RGBA", False)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.width, self.height,
                         GL_RGBA, GL_UNSIGNED_BYTE, data)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1, 1, 1, 1)

        #rysowanie prostokata
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(self.width, 0)
        glTexCoord2f(1, 1); glVertex2f(self.width, self.height)
        glTexCoord2f(0, 1); glVertex2f(0, self.height)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
