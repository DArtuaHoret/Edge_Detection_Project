"""Kompilacja i linkowanie programow shaderow (vertex + fragment)."""
from OpenGL.GL import *


# Kompiluje pojedynczy shader i sprawdza błędy
def compile_shader(source, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(shader).decode()
        raise RuntimeError(f"Blad kompilacji shadera:\n{error}")
    return shader

# Tworzy program shaderów z vertex i fragment shadera
def create_shader_program(vertex_path, fragment_path):
    with open(vertex_path, "r") as f:
        vertex_src = f.read()
    with open(fragment_path, "r") as f:
        fragment_src = f.read()

    vs = compile_shader(vertex_src, GL_VERTEX_SHADER)
    fs = compile_shader(fragment_src, GL_FRAGMENT_SHADER)

    program = glCreateProgram()
    glAttachShader(program, vs)
    glAttachShader(program, fs)
    glLinkProgram(program)

    if not glGetProgramiv(program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(program).decode()
        raise RuntimeError(f"Blad linkowania programu shaderow:\n{error}")

    glDeleteShader(vs)
    glDeleteShader(fs)
    return program
