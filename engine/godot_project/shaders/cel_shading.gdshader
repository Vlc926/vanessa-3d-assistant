shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_toon, specular_toon;

uniform vec4 albedo_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
uniform vec4 shadow_color : source_color = vec4(0.75, 0.72, 0.82, 1.0);
uniform float shadow_threshold : hint_range(-1.0, 1.0) = 0.15;
uniform float shadow_smoothness : hint_range(0.0, 1.0) = 0.05;
uniform vec4 rim_color : source_color = vec4(1.0, 0.95, 0.98, 1.0);
uniform float rim_threshold : hint_range(0.0, 1.0) = 0.65;
uniform float rim_smoothness : hint_range(0.0, 1.0) = 0.1;

void fragment() {
	vec4 tex = texture(albedo_texture, UV);
	vec4 base = albedo_color * tex;
	ALBEDO = base.rgb;
	ALPHA = base.a;
	ROUGHNESS = 0.85;
	METALLIC = 0.0;
}

void light() {
	float ndotl = dot(NORMAL, LIGHT);
	float light_intensity = smoothstep(shadow_threshold - shadow_smoothness, shadow_threshold + shadow_smoothness, ndotl);
	vec3 ramped_light = mix(shadow_color.rgb, vec3(1.0), light_intensity) * LIGHT_COLOR * ATTENUATION;
	
	float ndotv = 1.0 - max(0.0, dot(NORMAL, VIEW));
	float rim = smoothstep(rim_threshold - rim_smoothness, rim_threshold + rim_smoothness, ndotv) * light_intensity;
	vec3 rim_contribution = rim * rim_color.rgb * LIGHT_COLOR;
	
	DIFFUSE_LIGHT += ALBEDO * ramped_light + rim_contribution;
}
