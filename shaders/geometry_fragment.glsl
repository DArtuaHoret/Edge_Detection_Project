// Shader fragmentów pierwszego przebiegu renderowania. Zapisuje znormalizowane normalne do tekstury. 

#version 330 core

in vec3 v_view_normal;
out vec4 frag_normal;

void main() {

    frag_normal = vec4(normalize(v_view_normal), 1.0);

}
