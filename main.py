"""
Demonstrator shadera - Edge Rendering 
"""
import traceback
import numpy as np
import pygame
import pygame_gui
from pygame.locals import (
    DOUBLEBUF, OPENGL, RESIZABLE, QUIT, KEYDOWN, K_ESCAPE,
    VIDEORESIZE, K_w, K_s, K_a, K_d,
)
from OpenGL.GL import *

from camera import Camera
import mat_utils
from model_loader import load_obj_with_materials, make_fallback_cube
from shader_utils import create_shader_program
from gui import UIOverlay
from postprocessing import EdgeFramebuffer, FullscreenQuad

#### zabronienie wypisywania logów do terminalu
import logging
logging.getLogger("pywavefront").setLevel(logging.ERROR)

STATE_MENU = "MENU"
STATE_SCENE = "SCENE"

# Otwiera okno wyboru pliku OBJ
def pick_obj_file():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Wybierz model .obj",
        filetypes=[("Pliki Wavefront OBJ", "*.obj")],
    )
    root.destroy()
    return path


class App:
    def __init__(self):
        pygame.init()

        self.screen_w, self.screen_h = 1100, 700
        pygame.display.set_mode(
            (self.screen_w, self.screen_h), DOUBLEBUF | OPENGL | RESIZABLE
        )
        pygame.display.set_caption("Demonstrator shadera Edge Detection")

        glEnable(GL_DEPTH_TEST)
        glClearColor(0.08, 0.08, 0.10, 1.0)

        self.clock = pygame.time.Clock()

        self.state = STATE_MENU
        self.camera = Camera()

        # Główny obiekt sceny (scene_gotowe.obj albo własny .obj uzytkownika)
        self.mesh = None
        self.mesh_matrix = np.identity(4, dtype=np.float32)
        # Dodatkowe obiekty dekoracyjne domyślnej sceny: lista (mesh, model_matrix)
        self.scene_extras = []

        self.shader_mode = False
        self.camera_look_active = False

        self.scene_program = create_shader_program(
            "shaders/scene_vertex.glsl", "shaders/scene_fragment.glsl"
        )
        self.geometry_program = create_shader_program(
            "shaders/geometry_vertex.glsl", "shaders/geometry_fragment.glsl"
        )
        self.edge_program = create_shader_program(
            "shaders/edge_vertex.glsl", "shaders/edge_fragment.glsl"
        )

        self.edge_fbo = EdgeFramebuffer(self.screen_w, self.screen_h)
        self.fullscreen_quad = FullscreenQuad()

        self.camera_near = 0.1
        self.camera_far = 100.0

        self.depth_threshold = 0.15
        self.normal_threshold = 0.4

        self.menu_ui = UIOverlay(self.screen_w, self.screen_h)
        self.scene_ui = UIOverlay(self.screen_w, self.screen_h)
        self._build_menu_ui()
        self._build_scene_ui()

    # -- GUI --
    # Tworzy elementy głównego menu
    def _build_menu_ui(self):
        cx = self.screen_w // 2
        self.btn_load_default = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx - 170, 300, 340, 60),
            text="Zaladuj gotowa scene",
            manager=self.menu_ui.manager,
        )
        self.btn_load_custom = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(cx - 170, 380, 340, 60),
            text="Zaladuj wlasny obiekt (.obj)",
            manager=self.menu_ui.manager,
        )

    # Tworzy elementy interfejsu sceny
    def _build_scene_ui(self):
        self.btn_toggle_shader = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self.screen_w - 220, 20, 200, 50),
            text="Wyłacz shader" if self.shader_mode else "Uruchom shader",
            manager=self.scene_ui.manager,
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.screen_w - 220, 85, 200, 20),
            text="Prog: glebokosc",
            manager=self.scene_ui.manager,
        )
        self.slider_depth = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(self.screen_w - 220, 105, 200, 25),
            start_value=self.depth_threshold,
            value_range=(0.01, 2.0),
            manager=self.scene_ui.manager,
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(self.screen_w - 220, 140, 200, 20),
            text="Prog: normalne",
            manager=self.scene_ui.manager,
        )
        self.slider_normal = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(self.screen_w - 220, 160, 200, 25),
            start_value=self.normal_threshold,
            value_range=(0.05, 2.0),
            manager=self.scene_ui.manager,
        )

    # Przebudowuje GUI po zmianie rozmiaru okna
    def _rebuild_ui_for_resize(self):
        self.menu_ui.resize(self.screen_w, self.screen_h)
        self.scene_ui.resize(self.screen_w, self.screen_h)
        self._build_menu_ui()
        self._build_scene_ui()


    # -- Ładowanie sceny --

    # Usuwa aktualnie załadowane obiekty sceny
    def _reset_scene_objects(self):
        self.mesh = None
        self.scene_extras = []

    # Ładuje domyślną scenę wraz z dodatkowymi obiektami
    def load_default_scene(self):
        self._reset_scene_objects()
        try:
            self.mesh = load_obj_with_materials("models/scene_gotowe.obj")
            self.mesh_matrix = mat_utils.rotate_y_pos90_scale_translate(1.0, 4.05, 0.0, 4.05)

            self.scene_extras.append((
                load_obj_with_materials("models/bench_4.obj"),
                mat_utils.rotate_y_neg90_scale_translate(1.25, 4.5, 0.0, 3.6),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/cara_ic1_00001.obj"),
                mat_utils.rotate_y_pos90_scale_translate(0.03, 5.75, 0.0, 6.5),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/street_lamp_obj.obj"),
                mat_utils.scale_translate(0.005, 7.0, 0.0, 3.6),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/CCIDOOR2.obj"),
                mat_utils.rotate_y_pos90_scale_translate(1.2, 0.1, 0.0, 5.25),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/forest_nature_set_all_in.obj"),
                mat_utils.scale_translate(0.2, 6.7, 0.0, 4.0),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/tree02.obj"),
                mat_utils.scale_translate(0.16, 0.0, 0.0, 3.4),
            ))

            window_mesh = load_obj_with_materials("models/windows.obj")
            window_positions = [
                (0.1, 1, 7),
                (0.1, 1, 3.3),
                (0.1, 1, 1.3),
            ]
            for tx, ty, tz in window_positions:
                self.scene_extras.append((window_mesh, mat_utils.rotate_y_neg90_scale_translate(0.18, tx, ty, tz)))

            self.scene_extras.append((
                load_obj_with_materials("models/trash1.obj"),
                mat_utils.scale_translate(1.0, 6.25, 0.0, 3.6),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/Mailbox.obj"),
                mat_utils.rotate_y_neg90_scale_translate(0.04, 0.5, 0.9, 6.1),
            ))
            self.scene_extras.append((
                load_obj_with_materials("models/triple_recycling_bin.obj"),
                mat_utils.scale_translate(0.85, 2.5, 0.0, 0.5),
            ))

        except Exception:
            traceback.print_exc()
            print("Nie udalo sie zaladowac domyslnej sceny, uzyj kostki zastepczej.")
            self._reset_scene_objects()
            self.mesh = make_fallback_cube()

        self._enter_scene()

    # Ładuje wybrany przez użytkownika model 
    def load_custom_scene(self):
        path = pick_obj_file()
        if not path:
            return

        self._reset_scene_objects()
        try:
            self.mesh = load_obj_with_materials(path)
        except Exception as e:
            print(f"Nie udalo sie zaladowac modelu ({e}); uzyj kostki zastepczej.")
            self.mesh = make_fallback_cube()

        self._enter_scene()

    # Przełącza aplikację do widoku sceny
    def _enter_scene(self):
        self.state = STATE_SCENE

    # Włącza sterowanie kamerą za pomocą myszy
    def _start_camera_look(self):
        self.camera_look_active = True
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.get_rel()

    # Wyłącza sterowanie kamerą za pomocą myszy
    def _stop_camera_look(self):
        self.camera_look_active = False
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

    # Wraca z widoku sceny do menu głównego
    def _exit_to_menu(self):
        self.state = STATE_MENU
        self._stop_camera_look()

    # -- Petla glówna --
    # Uruchamia główną pętlę aplikacji
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            running = self._handle_events(dt)

            if self.state == STATE_SCENE:
                self._update_camera(dt)

            active_ui = self.menu_ui if self.state == STATE_MENU else self.scene_ui
            active_ui.update(dt)

            if self.state == STATE_SCENE:
                self.depth_threshold = self.slider_depth.get_current_value()
                self.normal_threshold = self.slider_normal.get_current_value()

            self._render()
            pygame.display.flip()

        pygame.quit()

    # Obsługuje zdarzenia wejściowe i zmianę stanu aplikacji
    def _handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == QUIT:
                return False

            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                if self.state == STATE_SCENE:
                    self._exit_to_menu()
                else:
                    return False

            elif event.type == VIDEORESIZE:
                self.screen_w, self.screen_h = event.w, event.h
                glViewport(0, 0, self.screen_w, self.screen_h)
                self.edge_fbo.resize(self.screen_w, self.screen_h)
                self._rebuild_ui_for_resize()

            elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                self._handle_button(event.ui_element)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if self.state == STATE_SCENE:
                    self._start_camera_look()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                if self.state == STATE_SCENE:
                    self._stop_camera_look()

            active_ui = self.menu_ui if self.state == STATE_MENU else self.scene_ui
            active_ui.process_event(event)

        return True

    # Obsługuje kliknięcia przycisków interfejsu
    def _handle_button(self, ui_element):
        if self.state == STATE_MENU:
            if ui_element == self.btn_load_default:
                self.load_default_scene()
            elif ui_element == self.btn_load_custom:
                self.load_custom_scene()
        elif self.state == STATE_SCENE:
            if ui_element == self.btn_toggle_shader:
                self.shader_mode = not self.shader_mode
                self.btn_toggle_shader.set_text(
                    "Wylacz shader" if self.shader_mode else "Uruchom shader"
                )

    # Aktualizuje pozycję i obrót kamery
    def _update_camera(self, dt):
        keys = pygame.key.get_pressed()
        keys_pressed = {
            'w': keys[K_w], 's': keys[K_s], 'a': keys[K_a], 'd': keys[K_d],
        }
        self.camera.process_keyboard(keys_pressed, dt)

        if self.camera_look_active:
            dx, dy = pygame.mouse.get_rel()
            if dx != 0 or dy != 0:
                self.camera.process_mouse(dx, dy)

    # -- Render --

    # Czyści ekran i renderuje aktualny widok
    def _render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.state == STATE_MENU:
            self._render_menu()
        elif self.state == STATE_SCENE:
            self._render_scene()

    # Renderuje interfejs menu głównego
    def _render_menu(self):
        self.menu_ui.draw()

    # na początku rysuj świat 3d, potem GUI w 2d
    # Renderuje scenę 3D oraz interfejs użytkownika
    def _render_scene(self):
        if self.shader_mode:
            self._render_edge_pipeline()
        else:
            self._render_normal_scene()

        self.scene_ui.draw()

    # Renderuje scenę z normalnym oświetleniem i teksturami
    def _render_normal_scene(self):
        """Zwykly podglad sceny."""
        glUseProgram(self.scene_program)

        view = self.camera.get_view_matrix()
        aspect = self.screen_w / max(self.screen_h, 1)
        projection = mat_utils.perspective(self.camera.fov, aspect, self.camera_near, self.camera_far)

        self._set_matrix(self.scene_program, "u_view", view)
        self._set_matrix(self.scene_program, "u_projection", projection)

        glUniform3f(glGetUniformLocation(self.scene_program, "u_light_dir"),
                    -0.4, -1.0, -0.3)
        glUniform3f(glGetUniformLocation(self.scene_program, "u_view_pos"),
                    *self.camera.position)

        if self.mesh:
            self._set_matrix(self.scene_program, "u_model", self.mesh_matrix)
            self.mesh.draw_with_material_setup(self.scene_program)

        for extra_mesh, model_matrix in self.scene_extras:
            self._set_matrix(self.scene_program, "u_model", model_matrix)
            extra_mesh.draw_with_material_setup(self.scene_program)

        glUseProgram(0)

    # Renderuje scenę w kilku etapach i nakłada wykryte krawędzie
    def _render_edge_pipeline(self):
        """Pipeline efektu 'kreskówkowego' nakładanego na normalną scenę:
        Przebieg 1: render całej sceny (glowny mesh + wszystkie dodatki)
                    do framebuffera (normalne + głębokość) tylko do wykrycia krawędzi.
        Przebieg 2: render ośweitlonej sceny z teksturami wprost na ekran (tak samo jak w trybie bez shadera).
        Przebieg 3: fullscreen quad (pełnoekranowy czworokąt) z shaderem Sobela, ktory czyta bufor z przebiegu 1
                    i dorysowuje białe kreski na wierzchu."""

        view = self.camera.get_view_matrix()
        aspect = self.screen_w / max(self.screen_h, 1)
        projection = mat_utils.perspective(self.camera.fov, aspect, self.camera_near, self.camera_far)

        # -- Przebieg 1: geometria -> framebuffer (tylko do wykrywania krawędzi) --
        self.edge_fbo.bind_for_writing()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glUseProgram(self.geometry_program)
        self._set_matrix(self.geometry_program, "u_view", view)
        self._set_matrix(self.geometry_program, "u_projection", projection)

        if self.mesh:
            self._set_matrix(self.geometry_program, "u_model", self.mesh_matrix)
            self.mesh.draw()

        # WAŻNE: wszystkie dodatkowe obiekty rysowane TUTAJ, przed unbind() -
        # inaczej trafiają mimo wszystko na ekran zamiast do bufora
        for extra_mesh, model_matrix in self.scene_extras:
            self._set_matrix(self.geometry_program, "u_model", model_matrix)
            extra_mesh.draw()

        glUseProgram(0)
        self.edge_fbo.unbind(self.screen_w, self.screen_h)

        # -- Przebieg 2: normalna, kolorowa scena -> ekran --
        # (ekran jest juz czysty - wyczyszczony na poczatku _render();
        # Przebieg 1 rysował do osobnego FBO, więc nie trzeba czyścić drugi raz)
        self._render_normal_scene()

        # -- Przebieg 3: nakładka Sobela (białe krawędzie) na wierzchu sceny --
        glUseProgram(self.edge_program)

        self.edge_fbo.bind_textures(normal_unit=0, depth_unit=1)
        glUniform1i(glGetUniformLocation(self.edge_program, "u_normal_tex"), 0)
        glUniform1i(glGetUniformLocation(self.edge_program, "u_depth_tex"), 1)

        texel_w = 1.0 / max(self.screen_w, 1)
        texel_h = 1.0 / max(self.screen_h, 1)
        glUniform2f(glGetUniformLocation(self.edge_program, "u_texel_size"),
                    texel_w, texel_h)

        glUniform1f(glGetUniformLocation(self.edge_program, "u_depth_threshold"),
                    self.depth_threshold)
        glUniform1f(glGetUniformLocation(self.edge_program, "u_normal_threshold"),
                    self.normal_threshold)
        glUniform1f(glGetUniformLocation(self.edge_program, "u_near"), self.camera_near)
        glUniform1f(glGetUniformLocation(self.edge_program, "u_far"), self.camera_far)

        # krawędź (alpha=1) nadpisuje scenę, reszta (alpha=0)
        # zostaje przezroczysta i przepuszcza to, co juz jest na ekranie
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.fullscreen_quad.draw()

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

        glUseProgram(0)

    # Przekazuje macierz do programu shadera
    def _set_matrix(self, program, name, matrix):
        loc = glGetUniformLocation(program, name)
        glUniformMatrix4fv(loc, 1, GL_TRUE, matrix)


if __name__ == "__main__":
    app = App()
    app.run()
