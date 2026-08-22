#version 330 core

in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_normal_tex;
uniform sampler2D u_depth_tex;
uniform vec2 u_texel_size;        // 1.0 / rozdzielczosc bufora (do przesuwania sie po sasiadach)
uniform float u_depth_threshold;  // prog czulosci dla glebokosci 
uniform float u_normal_threshold; // prog czulosci dla normalnych
uniform float u_near;             // bliska płaszczyzna kamery 
uniform float u_far;              // daleka płaszczyzna kamery 

//Przeliczenie na rzeczywistą odległość w jednostkach świata 
float linearize_depth(float raw_depth) {
    float ndc = raw_depth * 2.0 - 1.0;
    return (2.0 * u_near * u_far) / (u_far + u_near - ndc * (u_far - u_near));
}

// Filtr Sobela: liczy gradient w kierunku X i Y na siatce 3x3.
const vec2 OFFSETS[9] = vec2[](
    vec2(-1, -1), vec2(0, -1), vec2(1, -1),
    vec2(-1,  0), vec2(0,  0), vec2(1,  0),
    vec2(-1,  1), vec2(0,  1), vec2(1,  1)
);
const float KERNEL_X[9] = float[](-1.0, 0.0, 1.0, -2.0, 0.0, 2.0, -1.0, 0.0, 1.0);
const float KERNEL_Y[9] = float[](-1.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 2.0, 1.0);

void main() {
    float depth_gx = 0.0;
    float depth_gy = 0.0;
    vec3 normal_gx = vec3(0.0);
    vec3 normal_gy = vec3(0.0);

    for (int i = 0; i < 9; i++) {
        vec2 uv = v_texcoord + OFFSETS[i] * u_texel_size;

        float d = linearize_depth(texture(u_depth_tex, uv).r);
        vec3 n = texture(u_normal_tex, uv).rgb;

        depth_gx += d * KERNEL_X[i];
        depth_gy += d * KERNEL_Y[i];
        normal_gx += n * KERNEL_X[i];
        normal_gy += n * KERNEL_Y[i];
    }

    // dlugosc wektora gradientu (Gx, Gy)
    float depth_edge = length(vec2(depth_gx, depth_gy));
    float normal_edge = length(normal_gx) + length(normal_gy);

    //porownanie z progami
    float edge = 0.0;
    if (depth_edge > u_depth_threshold) {
        edge = 1.0;
    }
    if (normal_edge > u_normal_threshold) {
        edge = 1.0;
    }

    // biale krawedzie z alpha = edge - dzieki temu mozna to
    // nalozyc (blend) na kolorowa scene: tam gdzie nie ma krawedzi,
    // alpha=0 -> przezroczyste -> widac scene (teksturowana) pod spodem.
    frag_color = vec4(1.0, 1.0, 1.0, edge);
}
