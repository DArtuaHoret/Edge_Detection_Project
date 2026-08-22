"""
 - W/S/A/D - ruch do przodu/tyłu/w bok (względem kierunku patrzenia)
 - mysz (prawa) - obrót (yaw/pitch)
 - kólko - zoom 
"""
import math
import numpy as np

import mat_utils

# Jeśli po poruszeniu myszą w PRAWO kamera skręca w LEWO (i odwrotnie),
# przelączyć tą wartość na False (albo na True, jeśli jest teraz False).
INVERT_MOUSE_X = False

class Camera:
    def __init__(self, position=(2.0, 3.0, 8.0)):
        self.position = np.array(position, dtype=np.float32)

        self.yaw = -90.0  # patrzymy w stronę -Z na starcie
        self.pitch = 0.0

        self.world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self.move_speed = 4.0            
        self.mouse_sensitivity = 0.12
        self.scroll_sensitivity = 2.0

        self.fov = 60.0
        self.min_fov = 20.0
        self.max_fov = 90.0

        self._update_vectors()

    # Aktualizuje wektory kierunku kamery na podstawie yaw i pitch
    def _update_vectors(self):
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)

        front = np.array([
            math.cos(yaw_r) * math.cos(pitch_r),
            math.sin(pitch_r),
            math.sin(yaw_r) * math.cos(pitch_r),
        ], dtype=np.float32)
        self.front = front / np.linalg.norm(front)

        right = np.cross(self.front, self.world_up)
        self.right = right / np.linalg.norm(right)

        self.up = np.cross(self.right, self.front)

    # Przesuwa kamerę na podstawie wciśniętych klawiszy
    def process_keyboard(self, keys_pressed, dt):
        velocity = self.move_speed * dt
        if keys_pressed.get('w'):
            self.position += self.front * velocity
        if keys_pressed.get('s'):
            self.position -= self.front * velocity
        if keys_pressed.get('a'):
            self.position -= self.right * velocity
        if keys_pressed.get('d'):
            self.position += self.right * velocity

    # Obraca kamerę na podstawie ruchu myszy
    def process_mouse(self, dx, dy):
        if INVERT_MOUSE_X:
            dx = -dx
        self.yaw += dx * self.mouse_sensitivity
        self.pitch -= dy * self.mouse_sensitivity
        self.pitch = max(-89.0, min(89.0, self.pitch))
        self._update_vectors()

    # Zmienia pole widzenia kamery za pomocą scrolla (zoom)
    def process_scroll(self, wheel_amount):
        self.fov -= wheel_amount * self.scroll_sensitivity
        self.fov = max(self.min_fov, min(self.max_fov, self.fov))

    # Zwraca macierz widoku kamery
    def get_view_matrix(self):
        target = self.position + self.front
        return mat_utils.camera_Matrix(self.position, target, self.up)
