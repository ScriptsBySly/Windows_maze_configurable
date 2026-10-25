"""An animated vertical gradient that preserves the font's alpha mask."""

from ursina import Shader


vaporwave_text_shader = Shader(
    name='vaporwave_text',
    language=Shader.GLSL,
    vertex='''#version 130
        uniform mat4 p3d_ModelViewProjectionMatrix;
        in vec4 p3d_Vertex;
        in vec2 p3d_MultiTexCoord0;
        in vec4 p3d_Color;
        out vec2 texcoords;
        out vec4 vertex_color;

        void main() {
            gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
            texcoords = p3d_MultiTexCoord0;
            vertex_color = p3d_Color;
        }
    ''',
    fragment='''#version 130
        uniform sampler2D p3d_Texture0;
        uniform vec4 p3d_ColorScale;
        uniform float gradient_phase;
        uniform float viewport_height;
        uniform float label_center_y;
        uniform float label_height;
        uniform float outline_width;
        in vec2 texcoords;
        in vec4 vertex_color;
        out vec4 fragColor;

        void main() {
            float screen_y = gl_FragCoord.y / max(viewport_height, 1.0) - 0.5;
            float y = (screen_y - label_center_y) / max(label_height, 0.001);
            // A feature at constant phase travels toward increasing screen Y.
            float blend = 0.5 + 0.5 * cos(6.2831853 * (y - gradient_phase));
            vec3 pink = vec3(1.0, 0.15, 0.65);
            vec3 cyan = vec3(0.05, 0.95, 1.0);
            float fill = texture(p3d_Texture0, texcoords).a;
            float outline = fill;
            // UV derivatives keep the outline width in screen pixels.
            vec2 dx = dFdx(texcoords) * outline_width;
            vec2 dy = dFdy(texcoords) * outline_width;
            for (int i = 0; i < 12; ++i) {
                float angle = 6.2831853 * float(i) / 12.0;
                vec2 offset = cos(angle) * dx + sin(angle) * dy;
                outline = max(outline, texture(p3d_Texture0, texcoords + offset).a);
            }
            vec3 gradient = mix(pink, cyan, blend);
            vec3 rgb = mix(vec3(0.0), gradient, fill / max(outline, 0.0001));
            float alpha = outline * vertex_color.a * p3d_ColorScale.a;
            fragColor = vec4(rgb, alpha);
        }
    ''',
    default_input={
        'gradient_phase': 0.0,
        'viewport_height': 1920.0,
        'label_center_y': 0.0,
        'label_height': 0.15,
        'outline_width': 4.0,
    },
)
