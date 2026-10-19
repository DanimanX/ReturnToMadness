extends Area2D
class_name TentacleHazard
## Tentáculo que brota y se retrae. Solo hiere mientras está fuera.

@export var cycle_out: float = 1.1
@export var cycle_in: float = 1.6
@export var offset_phase: float = 0.0

var _sprite: AnimatedSprite2D
var _shape: CollisionShape2D
var _t: float = 0.0
var _out: bool = false
var _damage: float = 16.0


func setup() -> void:
	collision_layer = 8
	collision_mask = 2
	monitoring = true
	_damage = float(get_meta("damage", 16.0))
	_shape = get_node_or_null("Shape") as CollisionShape2D
	if _shape == null:
		_shape = CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = Vector2(14, 34)
		_shape.shape = rect
		_shape.position = Vector2(0, -17)
		_shape.name = "Shape"
		add_child(_shape)
	_sprite = get_node_or_null("Sprite") as AnimatedSprite2D
	if _sprite:
		_sprite.visible = false
	_t = offset_phase
	_apply(false)


func _apply(out: bool) -> void:
	_out = out
	if _shape:
		_shape.set_deferred("disabled", not out)
	if _sprite:
		_sprite.visible = out
		if out:
			_sprite.play("default")


func _physics_process(delta: float) -> void:
	_t += delta
	var period := cycle_out + cycle_in
	var phase := fmod(_t, period)
	var want := phase < cycle_out
	if want != _out:
		_apply(want)
		if want:
			AudioDirector.sfx("hit", 0.25, -18.0)
	if not _out:
		return
	for body in get_overlapping_bodies():
		if body is Player and body.has_method("take_damage"):
			body.take_damage(1.0, global_position)
			break
