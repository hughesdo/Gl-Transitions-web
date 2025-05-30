// Author: Fernando Kuteken
// License: MIT
#version 330

uniform sampler2D from; // First video texture
uniform sampler2D to; // Second video texture
uniform float progress; // Transition progress (0.0 to 1.0)
uniform vec2 resolution; // Resolution
uniform vec2 center; // = vec2(0.5, 0.5)
uniform float rotations; // = 1.0
uniform float scale; // = 8.0
uniform vec4 backColor; // = vec4(0.15, 0.15, 0.15, 1.0)

out vec4 outColor;

#define PI 3.14159265359

vec4 transition(vec2 uv) {
    vec2 difference = uv - center;
    vec2 dir = normalize(difference);
    float dist = length(difference);
    float angle = 2.0 * PI * rotations * progress;
    float c = cos(angle);
    float s = sin(angle);
    float currentScale = mix(scale, 1.0, 2.0 * abs(progress - 0.5));
    vec2 rotatedDir = vec2(dir.x * c - dir.y * s, dir.x * s + dir.y * c);
    vec2 rotatedUv = center + rotatedDir * dist / currentScale;
    if (rotatedUv.x < 0.0 || rotatedUv.x > 1.0 ||
        rotatedUv.y < 0.0 || rotatedUv.y > 1.0)
        return backColor;
    return mix(texture(from, rotatedUv), texture(to, rotatedUv), progress);
}

void main()
{
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    outColor = transition(uv);
}