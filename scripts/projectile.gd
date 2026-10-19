class_name Projectile
extends Area2D
## Proyectil genérico (bolas de los cultistas, escupitajos de los Mi-Go).

var velocity: Vector2 = Vector2.ZERO
var damage: float = 1.0
var color: Color = Color(0.8, 0.6, 1.0)
var life: float = 4.0
var _t: float = 0.0


static func spawn(parent: Node, pos: Vector2, vel: Vector2, dmg: float, col: Color) -> Projectile:
	if parent == null:
		return null
	var p := Projectile.new()
	p.position = pos
	p.velocity = vel
	p.damage = dmg
	p.color = col
	parent.add_child(p)
	return p


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	monitoring = true
	z_index = 3
	var cs := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 5.0
	cs.shape = c
	add_child(cs)
	body_entered.connect(_on_body)


func _physics_process(delta: float) -> void:
	_t += delta
	position += velocity * delta
	if _t >= life:
		queue_free()
	queue_redraw()


func _draw() -> void:
	draw_circle(Vector2.ZERO, 5.0, Color(color.r, color.g, color.b, 0.22))
	draw_circle(Vector2.ZERO, 3.0, color)
	draw_circle(Vector2(-1, -1), 1.2, Color(1, 1, 1, 0.9))
	if _t > 0.05:
		draw_line(Vector2.ZERO, -velocity.normalized() * 7.0, Color(color.r, color.g, color.b, 0.5), 1.5)


func _on_body(body: Node) -> void:
	if body is Player:
		body.take_damage(damage, global_position)
		queue_free()
