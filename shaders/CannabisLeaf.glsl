// Author: @Flexi23
// License: MIT
// Inspired by http://www.wolframalpha.com/input/?i=cannabis+curve
#version 330

uniform sampler2D from; // First video texture
uniform sampler2D to; // Second video texture
uniform float progress; // Transition progress (0.0 to 1.0)
uniform vec2 resolution; // Resolution
uniform float r; // = 0.5, leaf radius

out vec4 outColor;

vec4 transition(vec2 uv) {
    float prog = clamp(progress, 0.001, 1.0); // Avoid division by zero
    if (prog < 0.01) {
        return texture(from, uv);
    }
    vec2 leaf_uv = (uv - vec2(0.5)) / 2.0 / pow(prog, 1.0); // Larger, slower scaling
    leaf_uv.y += 0.2; // Reduced offset
    float o = atan(leaf_uv.y, leaf_uv.x);
    float leaf = 1.0 - length(leaf_uv) + r * (1.0 + sin(o)) * (1.0 + 0.9 * cos(8.0 * o)) * (1.0 + 0.1 * cos(24.0 * o)) * (0.9 + 0.05 * cos(200.0 * o));
    float t = smoothstep(0.5, 1.5, leaf); // Wider, softer transition
    // Debug: Highlight leaf area with white if t > 0.5
    if (t > 0.5) {
        return mix(vec4(1.0), texture(to, uv), 0.5); // White-tinted to texture
    }
    return texture(from, uv);
}

void main()
{
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    outColor = transition(uv);
}