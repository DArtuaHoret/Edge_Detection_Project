"""
Moduł odpowiedzialny za wczytywanie i zarządzanie trójwymiarową geometrią wraz z jej materiałami i teksturami
"""
import numpy as np
from OpenGL.GL import *
from PIL import Image
import os


#Klasa będąca obiektowym opakowaniem dla tekstury w systemie OpenGL
class Texture:
    def __init__(self, path):
        self.texture_id = None
        self.width = 0
        self.height = 0
        if path and os.path.exists(path):
            self._load(path)
    
    #Wczytuje plik graficzny (PNG/JPG) i inicjalizuje go jako teksturę
    def _load(self, path):
        try:
            img = Image.open(path)
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = np.array(img)
            
            self.width = img.width
            self.height = img.height
            
            if len(img_data.shape) == 2:
                img_data = np.stack([img_data] * 3, axis=-1)
            
            self.texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            
            if img_data.shape[2] == 4: 
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0,
                           GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            elif img_data.shape[2] == 3: 
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0,
                           GL_RGB, GL_UNSIGNED_BYTE, img_data)
            
            glBindTexture(GL_TEXTURE_2D, 0)
            print(f"Zaladowana tekstura: {os.path.basename(path)}")
        except Exception as e:
            print(f"Nie udalo sie zaladowac tekstury {path}: {e}")
            self.texture_id = None
    
    #Aktywuje i podłącza teksturę do wybranego obiektu bezpośrednio przed renderowaniem
    def bind(self, unit=0):
        if self.texture_id:
            glActiveTexture(GL_TEXTURE0 + unit)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)


#Klasa definiująca właściwości optyczne powierzchni obiektu 3D
class Material:
    def __init__(self, name):
        self.name = name
        self.color = np.array([0.7, 0.75, 0.8], dtype=np.float32) 
        self.texture = None
        self.use_texture = False
    
    #Ustawia podstawowy kolor dyfuzyjny materiału, zdefiniowany w formacie RGB
    def set_color(self, r, g, b):
        self.color = np.array([r, g, b], dtype=np.float32)
    
    #Przypisuje obiekt tekstury do danego materiału i ustawia flagę informującą shader o konieczności jej użycia
    def set_texture(self, texture):
        if isinstance(texture, Texture) and texture.texture_id:
            self.texture = texture
            self.use_texture = True


#Reprezentuje spójny fragment siatki geometrycznej (modelu), który współdzieli dokładnie jeden materiał
class SubMesh:
    def __init__(self, vertices, normals, uvs, indices, material=None):
        self.vertex_count = len(indices)
        self.material = material
        
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        vbo_pos = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_pos)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)
        
        vbo_norm = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_norm)
        glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(1)
        
        vbo_uv = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_uv)
        glBufferData(GL_ARRAY_BUFFER, uvs.nbytes, uvs, GL_STATIC_DRAW)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(2)
        
        ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        glBindVertexArray(0)

    #Wysyła żądanie renderowania geometrii do OpenGL na podstawie powiązanych buforów
    def draw(self):
        if not self.material:
            return
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.vertex_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)


#Główny kontener reprezentujący kompletny model trójwymiarowy
class Mesh:
    def __init__(self):
        self.submeshes = []
    
    #Dodaje nowy fragment geometrii do globalnej listy submeshów wchodzących w skład całego modelu
    def add_submesh(self, submesh):
        self.submeshes.append(submesh)
    
    #Renderuje wszystkie submeshe modelu sekwencyjnie
    def draw(self):
        for submesh in self.submeshes:
            submesh.draw()
    
    #Renderuje wszystkie submeshe, uprzednio przesyłając do shadera właściwości materiału (kolor oraz teksturę) przypisanego do konkretnego fragmentu modelu
    def draw_with_material_setup(self, shader_program):
        for submesh in self.submeshes:
            
            if submesh.material:
                color_loc = glGetUniformLocation(shader_program, "u_object_color")
                glUniform3f(color_loc, *submesh.material.color)
                
                use_tex_loc = glGetUniformLocation(shader_program, "u_use_texture")
                if submesh.material.use_texture and submesh.material.texture:
                    submesh.material.texture.bind(0)
                    glUniform1i(glGetUniformLocation(shader_program, "u_texture"), 0)
                    glUniform1i(use_tex_loc, 1)
                else:
                    glUniform1i(use_tex_loc, 0)
            
            submesh.draw()

#Oblicza uśrednione wektory normalne dla każdego wierzchołka
def compute_smooth_normals(vertices, indices):
    normals = np.zeros_like(vertices)
    tris = indices.reshape(-1, 3)

    for tri in tris:
        v0, v1, v2 = vertices[tri[0]], vertices[tri[1]], vertices[tri[2]]
        face_normal = np.cross(v1 - v0, v2 - v0)
        for idx in tri:
            normals[idx] += face_normal

    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1.0
    normals = normals / lengths[:, None]
    return normals

#    Główna funkcja ładująca. Parsuje plik .obj oraz powiązane pliki materiałów .mtl, przekształca dane wierzchołków i rozdziela geometrię na poszczególne obiekty SubMesh ze skonfigurowanymi materiałami
def load_obj_with_materials(obj_path, mtl_dir=None):
    import pywavefront
    import os
    import numpy as np

    if mtl_dir is None:
        mtl_dir = os.path.dirname(obj_path)

    scene = pywavefront.Wavefront(obj_path, collect_faces=True, create_materials=True)
    mesh = Mesh()

    for mat_name, obj_material in scene.materials.items():
        print("MATERIAL:", mat_name)
        if not obj_material.vertices:
            continue

        flat = np.array(obj_material.vertices, dtype=np.float32)
        fmt = obj_material.vertex_format

        if fmt == 'T2F_N3F_V3F':
            reshaped = flat.reshape(-1, 8)
            uvs = reshaped[:, 0:2].copy()

            normals = reshaped[:, 2:5]
            mesh_vertices = reshaped[:, 5:8]
            mesh_indices = np.arange(len(mesh_vertices), dtype=np.uint32)
            
        elif fmt == 'N3F_V3F':
            reshaped = flat.reshape(-1, 6)
            normals = reshaped[:, 0:3]
            mesh_vertices = reshaped[:, 3:6]
            mesh_indices = np.arange(len(mesh_vertices), dtype=np.uint32)
            uvs = np.zeros((len(mesh_vertices), 2), dtype=np.float32)
        else: 
            mesh_vertices = flat.reshape(-1, 3)
            mesh_indices = np.arange(len(mesh_vertices), dtype=np.uint32)
            normals = compute_smooth_normals(mesh_vertices, mesh_indices)
            uvs = np.zeros((len(mesh_vertices), 2), dtype=np.float32)

        material = Material(mat_name)
        material.set_color(*obj_material.diffuse[:3])
        name_lower = mat_name.lower()
        tex_path = None

        if obj_material.texture and obj_material.texture.path:
            tex_path = obj_material.texture.path
            if not os.path.isabs(tex_path):
                tex_path = os.path.join(mtl_dir, os.path.basename(tex_path))

        if tex_path and os.path.exists(tex_path):
            material.set_texture(Texture(tex_path))
            
        submesh = SubMesh(mesh_vertices.flatten(), normals.flatten(), uvs.flatten(), mesh_indices, material)
        mesh.add_submesh(submesh)

    return mesh

#Generuje prosty sześcian. Służy jako mechanizm awaryjny w przypadku niepowodzenia ładowania modelu z pliku zewnętrznego.
def make_fallback_cube():
    positions = np.array([
        # przód (+Z)
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
        # tył (-Z)
        [1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1],
        # lewo (-X)
        [-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1],
        # prawo (+X)
        [1, -1, 1], [1, -1, -1], [1, 1, -1], [1, 1, 1],
        # góra (+Y)
        [-1, 1, 1], [1, 1, 1], [1, 1, -1], [-1, 1, -1],
        # dół (-Y)
        [-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1],
    ], dtype=np.float32)

    face_normals = np.array([
        [0, 0, 1], [0, 0, -1], [-1, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0],
    ], dtype=np.float32)
    normals = np.repeat(face_normals, 4, axis=0)

    indices = np.array(indices, dtype=np.uint32)
    uvs = np.zeros((24, 2), dtype=np.float32)

    mesh = Mesh()
    material = Material("cube_default")
    material.set_color(0.7, 0.75, 0.8)
    submesh = SubMesh(positions.flatten(), normals.flatten(), uvs.flatten(), indices, material)
    mesh.add_submesh(submesh)
    
    return mesh