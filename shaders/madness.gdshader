shader_type canvas_item;
render_mode unshaded;

// Post-proceso de LOCURA. Todo se controla con `madness` (0..1).
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest, repeat_disable;

uniform float madness : hint_range(0.0, 1.0) = 0.0;
uniform float sanity : hint_range(0.0, 1.0) = 1.0;
uniform float hurt_flash : hint_range(0.0, 1.0) = 0.0;
uniform float voice_flash : hint_range(0.0, 1.0) = 0.0;
uniform vec4 tint : source_color = vec4(0.42, 0.78, 0.62, 1.0);
uniform vec2 resolution = vec2(480.0, 270.0);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 uv = SCREEN_UV;
	vec2 c = uv - 0.5;

	// --- onda: la geometría respira ---
	float wob = madness * madness;
	uv.x += sin(uv.y * 21.0 + TIME * 1.15) * 0.0075 * wob;
	uv.y += cos(uv.x * 15.0 + TIME * 0.83) * 0.0055 * wob;
	uv += c * sin(TIME * 0.9) * 0.004 * wob;

	// --- aberración cromática ---
	float ca = 0.0004 + madness * 0.0016;
	vec3 col;
	col.r = texture(screen_texture, uv + vec2(ca, ca * 0.4)).r;
	col.g = texture(screen_texture, uv).g;
	col.b = texture(screen_texture, uv - vec2(ca, -ca * 0.4)).b;

	// --- viñeta (más cerrada con locura y con poca cordura) ---
	float vig = 1.0 - dot(c, c) * (0.55 + madness * 0.75 + (1.0 - sanity) * 0.55);
	col *= clamp(vig, 0.0, 1.0);

	// --- grano ---
	float n = hash(uv * resolution + vec2(TIME * 37.0, TIME * 17.0));
	col += (n - 0.5) * (0.022 + madness * 0.040);

	// --- líneas de escaneo ---
	float scan = step(0.5, fract(SCREEN_UV.y * resolution.y * 0.5));
	col *= 1.0 - scan * (0.025 + madness * 0.04);

	// --- pulso de bordes (el mundo late) ---
	float edge = smoothstep(0.22, 0.72, length(c));
	float pulse = 0.5 + 0.5 * sin(TIME * 1.6);
	col += tint.rgb * edge * madness * 0.045 * (0.55 + 0.45 * pulse);

	// --- desaturación + tinte enfermizo ---
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(col, vec3(lum) * tint.rgb * 1.45, madness * 0.14);

	// --- tensión baja: el color se va ---
	col = mix(col, vec3(lum) * vec3(0.85, 0.95, 1.0), (1.0 - sanity) * 0.18);

	// --- exposición: el arte es oscuro, pero tiene que leerse ---
	col = pow(max(col, vec3(0.0)), vec3(0.93)) * 1.03;

	// --- destellos ---
	col = mix(col, vec3(0.55, 0.04, 0.05), hurt_flash * 0.42);
	col = mix(col, vec3(0.80, 0.82, 0.70), voice_flash * 0.30);

	COLOR = vec4(col, 1.0);
}
