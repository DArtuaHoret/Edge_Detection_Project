#version 330 core
""" 
    Shader wierzchołków normalnego renderowania. Przekształca wierzchołki obiektu oraz przekazuje do shadera 
    fragmentów pozycję, normalną i współrzędne tekstury potrzebne do oświetlenia oraz teksturowania.
"""

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoord;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

out vec3 v_Normal;
out vec3 v_FragPos;
out vec2 v_TexCoord;

void main() {
    gl_Position = u_projection * u_view * u_model * vec4(aPos, 1.0);

    //polozeia wierzcholka w swiecie (nie w kamerze)
    v_FragPos = vec3(u_model * vec4(aPos, 1.0));  

    v_Normal = mat3(transpose(inverse(u_model))) * aNormal;
    v_TexCoord = aTexCoord;
}
