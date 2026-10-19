class_name CameraShake
extends RefCounted
## Temblor de cámara simple y reutilizable.

static func shake(cam: Camera2D, duration: float, strength: float) -> void:
	if cam == null or not is_instance_valid(cam):
		return
	var prev: Variant = cam.get_meta("shake_tween") if cam.has_meta("shake_tween") else null
	if prev is Tween and prev.is_valid():
		prev.kill()
	var tw := cam.create_tween()
	cam.set_meta("shake_tween", tw)
	var steps := maxi(4, int(duration * 30.0))
	var step_t := duration / float(steps)
	for i in steps:
		var falloff := 1.0 - float(i) / float(steps)
		var off := Vector2(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * strength * falloff
		tw.tween_property(cam, "offset", off, step_t)
	tw.tween_property(cam, "offset", Vector2.ZERO, 0.06)
