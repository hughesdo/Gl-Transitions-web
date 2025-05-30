// Author: Fernando Kuteken
// License: MIT
// Hexagonal math from: http://www.redblobgames.com/grids/hexagons/
#version 330

uniform sampler2D from; // First video texture
uniform sampler2D to; // Second video texture
uniform float progress; // Transition progress (0.0 to 1.0)
uniform vec2 resolution; // Resolution
uniform int steps; // = 50
uniform float horizontalHexagons; // = 20.0

out vec4 outColor;

struct Hexagon {
    float q;
    float r;
    float s;
};

Hexagon createHexagon(float q, float r) {
    Hexagon hex;
    hex.q = q;
    hex.r = r;
    hex.s = -q - r;
    return hex;
}

Hexagon roundHexagon(Hexagon hex) {
    float q = floor(hex.q + 0.5);
    float r = floor(hex.r + 0.5);
    float s = floor(hex.s + 0.5);
    float deltaQ = abs(q - hex.q);
    float deltaR = abs(r - hex.r);
    float deltaS = abs(s - hex.s);
    if (deltaQ > deltaR && deltaQ > deltaS)
        q = -r - s;
    else if (deltaR > deltaS)
        r = -q - s;
    else
        s = -q - r;
    return createHexagon(q, r);
}

Hexagon hexagonFromPoint(vec2 point, float size) {
    point.y /= 1.0; // Assuming ratio = 1.0, adjust if needed
    point = (point - 0.5) / size;
    float q = (sqrt(3.0) / 3.0) * point.x + (-1.0 / 3.0) * point.y;
    float r = 0.0 * point.x + 2.0 / 3.0 * point.y;
    Hexagon hex = createHexagon(q, r);
    return roundHexagon(hex);
}

vec2 pointFromHexagon(Hexagon hex, float size) {
    float x = (sqrt(3.0) * hex.q + (sqrt(3.0) / 2.0) * hex.r) * size + 0.5;
    float y = (0.0 * hex.q + (3.0 / 2.0) * hex.r) * size + 0.5;
    return vec2(x, y * 1.0); // Assuming ratio = 1.0
}

vec4 transition(vec2 uv) {
    float dist = 2.0 * min(progress, 1.0 - progress);
    dist = steps > 0 ? ceil(dist * float(steps)) / float(steps) : dist;
    float size = (sqrt(3.0) / 3.0) * dist / horizontalHexagons;
    vec2 point = dist > 0.0 ? pointFromHexagon(hexagonFromPoint(uv, size), size) : uv;
    return mix(texture(from, point), texture(to, point), progress);
}

void main()
{
    vec2 uv = gl_FragCoord.xy / resolution.xy;
    outColor = transition(uv);
}