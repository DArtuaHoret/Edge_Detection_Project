#version 330 core

layout(location = 0) in vec3 in_position;
layout(location = 1) in vec3 in_normal;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

out vec3 v_view_normal;

void main() {
    mat4 model_view = u_view * u_model;
    vec4 view_pos = model_view * vec4(in_position, 1.0);

    // normalna w przestrzeni kamery (a nie swiata)
    v_view_normal = mat3(transpose(inverse(model_view))) * in_normal;

    gl_Position = u_projection * view_pos;
}
