// Shader fragmentów normalnego renderowania. Implementuje tekstury oraz oblicza oświetlenie. 

#version 330 core
in vec3 v_Normal;
in vec3 v_FragPos;
in vec2 v_TexCoord;

out vec4 FragColor;

uniform vec3 u_light_dir;
uniform vec3 u_view_pos;
uniform vec3 u_object_color;
uniform sampler2D u_texture;
uniform bool u_use_texture;

void main() {
    vec3 color = u_object_color;
    
    if (u_use_texture) {
        if (length(v_TexCoord) < 0.0001) {
            vec3 blend_weights = abs(normalize(v_Normal));
            blend_weights = (blend_weights - 0.2) * 7.0;
            blend_weights = max(blend_weights, 0.0);
            blend_weights /= (blend_weights.x + blend_weights.y + blend_weights.z);
            
            vec2 coord1 = v_FragPos.zy * 0.5;   // было .yz
			vec2 coord2 = v_FragPos.xz * 0.5;   // было .zx
			vec2 coord3 = v_FragPos.xy * 0.5;   // без изменений
            
            vec3 col1 = texture(u_texture, coord1).rgb;
            vec3 col2 = texture(u_texture, coord2).rgb;
            vec3 col3 = texture(u_texture, coord3).rgb;
            
            color = col1 * blend_weights.x + col2 * blend_weights.y + col3 * blend_weights.z;
        } else {
            color = texture(u_texture, v_TexCoord).rgb;
        }
    }

    float ambient = 0.3;

    // normalizacja, bo normalne 10 i 1 patrzą w te sama strone
    vec3 norm = normalize(v_Normal);

    // pozycja źródła śwaitła 
    vec3 lightDir = normalize(-u_light_dir);
    float diff = max(dot(norm, lightDir), 0.0);
    
    // pozycja obserwatora
    vec3 viewDir = normalize(u_view_pos - v_FragPos);
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(norm, halfwayDir), 0.0), 32.0);
    float specular = 0.5 * spec;

    vec3 result = color * (ambient + diff) + vec3(specular);
    FragColor = vec4(result, 1.0);
}
