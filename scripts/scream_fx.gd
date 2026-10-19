class_name ScreamFX
extends RefCounted
## Onda de La Voz: anillos que se expanden.

static func spawn(parent: Node, pos: Vector2, radius: float) -> void:
	if parent == null:
		return
	var fx := ScreamRing.new()
	fx.max_radius = radius
	fx.position = pos
	fx.z_index = 6
	parent.add_child(fx)


class ScreamRing extends Node2D:
	var max_radius: float = 96.0
	var t: float = 0.0
	var dur: float = 0.5

	func _process(delta: float) -> void:
		t += delta
		queue_redraw()
		if t >= dur:
			queue_free()

	func _draw() -> void:
		var k := clampf(t / dur, 0.0, 1.0)
		var r := max_radius * ease(k, 0.4)
		var a := (1.0 - k) * 0.85
		draw_arc(Vector2.ZERO, r, 0.0, TAU, 48, Color(0.86, 0.92, 0.78, a), 2.0, true)
		if k < 0.7:
			draw_arc(Vector2.ZERO, r * 0.72, 0.0, TAU, 40,
					Color(0.70, 0.80, 0.95, a * 0.6), 1.0, true)
		# espinas del grito
		for i in 8:
			var ang := TAU * float(i) / 8.0 + t * 2.0
			var p0 := Vector2(cos(ang), sin(ang)) * r * 0.85
			var p1 := Vector2(cos(ang), sin(ang)) * r * 1.08
			draw_line(p0, p1, Color(0.95, 0.98, 0.86, a * 0.8), 1.0)
