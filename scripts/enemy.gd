extends CharacterBody2D
class_name Enemy
## Criatura genérica. El comportamiento se elige por `kind`.

signal killed

const STATS := {
	"ahogado":  {"hp": 2.0, "speed": 30.0, "dmg": 1.0, "aggro": 168.0, "range": 22.0, "cd": 1.3, "fly": false, "frames": 2, "fps": 4.0, "h": 30},
	"cultista": {"hp": 2.0, "speed": 20.0, "dmg": 1.0, "aggro": 220.0, "range": 150.0, "cd": 1.9, "fly": false, "frames": 2, "fps": 3.0, "h": 34},
	"polipo":   {"hp": 1.0, "speed": 42.0, "dmg": 1.0, "aggro": 200.0, "range": 20.0, "cd": 1.1, "fly": true, "frames": 2, "fps": 5.0, "h": 26},
	"bestia":   {"hp": 3.5, "speed": 68.0, "dmg": 1.0, "aggro": 230.0, "range": 26.0, "cd": 1.6, "fly": false, "frames": 2, "fps": 5.0, "h": 28},
	"migo":     {"hp": 2.0, "speed": 36.0, "dmg": 1.0, "aggro": 210.0, "range": 24.0, "cd": 1.2, "fly": true, "frames": 2, "fps": 4.0, "h": 28},
	"espectro": {"hp": 0.1, "speed": 22.0, "dmg": 0.0, "aggro": 200.0, "range": 20.0, "cd": 99.0, "fly": true, "frames": 1, "fps": 4.0, "h": 44},
}

var kind: String = "ahogado"
var level: Level = null
var hp: float = 2.0
var speed: float = 30.0
var damage: float = 1.0
var aggro: float = 170.0
var attack_range: float = 24.0
var attack_cd: float = 1.3
var flying: bool = false
var sprite_h: int = 30

var _sprite: AnimatedSprite2D
var _cd: float = 0.0
var _dead: bool = false
var _stun: float = 0.0
var _knock: Vector2 = Vector2.ZERO
var _facing: int = -1
var _home: Vector2
var _patrol_phase: float = 0.0
var _windup: float = 0.0
var _flash: float = 0.0
var _contact_cd: float = 0.0
var _rage: float = 0.0
var _hit_area: Area2D
var _gravity: float = 980.0
var _config: Dictionary = {}


func _ready() -> void:
	add_to_group("enemies")
	_config = STATS.get(kind, STATS["ahogado"])
	hp = float(_config["hp"]) * (1.0 + GameState.madness * 0.05)
	speed = _config["speed"]
	damage = _config["dmg"]
	aggro = _config["aggro"]
	attack_range = _config["range"]
	attack_cd = _config["cd"]
	flying = _config["fly"]
	_rage = GameState.madness_ratio()
	# a más locura, antes te detectan
	aggro *= 1.0 + _rage * 0.45
	speed *= 1.0 + _rage * 0.22

	collision_layer = 4
	collision_mask = 1 if not flying else 0
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING if flying else CharacterBody2D.MOTION_MODE_GROUNDED
	z_index = 2
	_home = position

	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(14, 22)
	shape.shape = rect
	shape.position = Vector2(0, -11)
	add_child(shape)

	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = _frames()
	_sprite.centered = false
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_sprite.animation = "default"
	_sprite.play()
	add_child(_sprite)
	_position_sprite()

	_hit_area = Area2D.new()
	_hit_area.collision_layer = 0
	_hit_area.collision_mask = 2
	_hit_area.monitoring = true
	var hs := CollisionShape2D.new()
	var hr := RectangleShape2D.new()
	hr.size = Vector2(20, 24)
	hs.shape = hr
	hs.position = Vector2(0, -12)
	_hit_area.add_child(hs)
	add_child(_hit_area)
	_hit_area.body_entered.connect(_on_touch)


func _frames() -> SpriteFrames:
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	sf.add_animation("default")
	var base := "res://assets/sprites/en_%s" % kind
	var n: int = _config["frames"]
	for i in n:
		var p := "%s_%d.png" % [base, i]
		if not ResourceLoader.exists(p):
			p = base + ".png"
		if ResourceLoader.exists(p):
			sf.add_frame("default", load(p))
	sf.set_animation_speed("default", _config["fps"])
	sf.set_animation_loop("default", true)
	return sf


func _position_sprite() -> void:
	var tex := _sprite.sprite_frames.get_frame_texture("default", 0)
	var w: int = tex.get_width() if tex else 24
	var h: int = tex.get_height() if tex else 30
	sprite_h = h
	_sprite.offset = Vector2(-w * 0.5, -h)


func is_dead() -> bool:
	return _dead


func stun(t: float) -> void:
	_stun = maxf(_stun, t)
	_windup = 0.0
	if kind == "espectro":
		_dissolve()


func take_hit(amount: float, from: Vector2, knockback: float = 120.0) -> void:
	if _dead:
		return
	if kind == "espectro":
		_dissolve()
		return
	hp -= amount
	_flash = 0.12
	var dir := signf(global_position.x - from.x)
	if dir == 0.0:
		dir = 1.0
	_knock = Vector2(dir * knockback, -60.0)
	_stun = maxf(_stun, 0.22)
	if hp <= 0.0:
		_die()


func _die() -> void:
	_dead = true
	GameState.add_kill_madness(0.028)
	GameState.add_clarity(3.0)
	level_hit_feedback()
	AudioDirector.sfx("hit", 0.2, -8.0)
	_spawn_death_fx()
	killed.emit()
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 0.35)
	tw.tween_callback(queue_free)


func _dissolve() -> void:
	if _dead:
		return
	_dead = true
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 0.6)
	tw.tween_callback(queue_free)


func level_hit_feedback() -> void:
	if level and level.camera:
		CameraShake.shake(level.camera, 0.12, 1.6)


func _spawn_death_fx() -> void:
	var p := CPUParticles2D.new()
	p.position = Vector2(0, -sprite_h * 0.4)
	p.emitting = true
	p.one_shot = true
	p.amount = 18
	p.lifetime = 0.55
	p.explosiveness = 0.9
	p.direction = Vector2(0, -1)
	p.spread = 70.0
	p.initial_velocity_min = 30.0
	p.initial_velocity_max = 110.0
	p.gravity = Vector2(0, 220)
	p.scale_amount_min = 1.0
	p.scale_amount_max = 2.0
	p.color = Color(0.55, 0.16, 0.18, 0.9)
	p.z_index = 5
	add_child(p)


func _on_touch(body: Node) -> void:
	if _dead or _contact_cd > 0.0 or damage <= 0.0:
		return
	if body is Player:
		body.take_damage(damage, global_position)
		_contact_cd = 0.9


func _physics_process(delta: float) -> void:
	if _dead:
		return
	_cd = maxf(0.0, _cd - delta)
	_contact_cd = maxf(0.0, _contact_cd - delta)
	_flash = maxf(0.0, _flash - delta)
	_sprite.modulate = Color(2.2, 2.2, 2.2) if _flash > 0.0 else Color.WHITE

	if _stun > 0.0:
		_stun -= delta
		_knock = _knock.move_toward(Vector2.ZERO, 400.0 * delta)
		velocity = _knock
		if flying:
			position += _knock * delta
			_knock = Vector2.ZERO
			velocity = Vector2.ZERO
		else:
			velocity.y = minf(velocity.y + _gravity * delta, 430.0)
			move_and_slide()
		return

	var player := _find_player()
	if flying:
		_fly_behavior(delta, player)
	else:
		_ground_behavior(delta, player)

	if _windup > 0.0:
		_windup -= delta
		_sprite.modulate = Color(1.6, 1.2, 1.2)
		if _windup <= 0.0:
			_execute_attack(player)


func _find_player() -> Player:
	if level and level.player and is_instance_valid(level.player):
		return level.player
	return null


func _ground_behavior(delta: float, player: Player) -> void:
	var target_dir := 0.0
	var dist := INF
	if player:
		dist = global_position.distance_to(player.global_position)
		if dist < aggro:
			target_dir = signf(player.global_position.x - global_position.x)
	if target_dir == 0.0:
		_patrol_phase += delta
		target_dir = signf(sin(_patrol_phase * 0.6))
		if is_on_wall():
			_patrol_phase += PI

	velocity.x = move_toward(velocity.x, target_dir * speed, 420.0 * delta)
	if target_dir != 0.0:
		_facing = 1 if target_dir > 0.0 else -1
	_sprite.flip_h = _facing < 0

	velocity.y = minf(velocity.y + _gravity * delta, 430.0)
	move_and_slide()

	# ataque
	if player and dist < attack_range + 26.0 and _cd <= 0.0:
		_cd = attack_cd
		if kind == "cultista":
			_cast_bolt(player)
		else:
			_windup = 0.28


func _fly_behavior(delta: float, player: Player) -> void:
	var target := _home + Vector2(sin(Time.get_ticks_msec() * 0.0013 + _patrol_phase) * 30.0, 0)
	_patrol_phase += delta
	if player and global_position.distance_to(player.global_position) < aggro:
		target = player.global_position + Vector2(0, -18)
	var dir := (target - global_position)
	if dir.length() > 4.0:
		dir = dir.normalized()
	position += dir * speed * delta
	_facing = 1 if dir.x > 0.0 else -1
	_sprite.flip_h = _facing < 0
	_sprite.position.y = sin(Time.get_ticks_msec() * 0.006 + _patrol_phase) * 2.0

	if player and kind == "migo" and _cd <= 0.0 and global_position.distance_to(player.global_position) < 170.0:
		_cd = attack_cd
		_cast_bolt(player)


func _execute_attack(player: Player) -> void:
	if player == null:
		return
	if kind == "bestia":
		var dir := signf(player.global_position.x - global_position.x)
		_knock = Vector2(dir * 210.0, -40.0)
		_stun = 0.22
	else:
		if global_position.distance_to(player.global_position) < attack_range + 30.0:
			player.take_damage(damage, global_position)


func _cast_bolt(player: Player) -> void:
	if player == null:
		return
	var dir := (player.global_position + Vector2(0, -14) - global_position).normalized()
	Projectile.spawn(get_parent(), global_position + Vector2(0, -18), dir * 130.0,
			damage, Color(0.72, 0.55, 0.95))
	AudioDirector.sfx("swing", 0.2, -12.0)
