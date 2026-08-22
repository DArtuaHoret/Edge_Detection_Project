"""
potok MVP — Model, View, Projection
"""
import numpy as np
import math


def perspective(fov_deg, aspect, near, far):
    """Macierz projekcji perspektywicznej. Przyjmuje pionowy kąt widzenia, proporcję ekranu, odległości near i fear.
    rzutowanie perspektywiczne."""
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0) 
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m



def camera_Matrix(eye, target, up):
    """Macierz widoku."""
    f = target - eye
    f = f / np.linalg.norm(f)
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    u = np.cross(s, f)

    m = np.identity(4, dtype=np.float32)
    m[0, 0:3] = s
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m

def scale_translate(s, tx, ty, tz):
    """Jednolite skalowanie + przesuniecie, bez obrotu."""
    return np.array([
        [s,   0.0, 0.0, tx],
        [0.0, s,   0.0, ty],
        [0.0, 0.0, s,   tz],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float32)


def rotate_y_neg90_scale_translate(s, tx, ty, tz):
    """Obrót -90 stopni wokół Y + skalowanie (ławka, okna, skrzynka)."""
    return np.array([
        [0.0, 0.0, s,   tx],
        [0.0, s,   0.0, ty],
        [-s,  0.0, 0.0, tz],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float32)


def rotate_y_pos90_scale_translate(s, tx, ty, tz):
    """Obrót +90 stopni wokół Y + skalowanie (kareta, drzwi)."""
    return np.array([
        [0.0, 0.0, -s,  tx],
        [0.0, s,   0.0, ty],
        [s,   0.0, 0.0, tz],
        [0.0, 0.0, 0.0, 1.0],
    ], dtype=np.float32)

