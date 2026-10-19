extends CharacterBody2D
class_name Boss
## Guardián de etapa. Tres fases, patrones distintos según la etapa.

signal defeated
signal activated
signal health_changed(ratio: float, label: String)

const SPRITES := [
	"boss_sacerdote", "boss_madre", "boss_bibliotecario", "boss_cazador",
	"boss_ingeniero", "boss_espejo", "boss_cthulhu",
]
const PATTERNS := [
	["volley", "slam", "rain"],
	["summon", "slam", "volley"],
	["volley", "gaze", "rain"],
	["charge", "slam", "rain"],
	["volley", "summon", "rain"],
	["charge", "gaze", "volley"],
	["gaze", "rain", "summon", "slam"],
]

var boss_index: int = 0
var level: Level = null
var label: String = ""
var max_hp: float = 24.0
var hp: float = 24.0
var phase: int = 1
var active: bool = false
var _dead: bool = false

var _sprite: AnimatedSprite2D
var _sprite_w: int = 48
var _sprite_h: int = 64
var _cooldown: float = 2.0
var _attack: String = ""
var _at: float = 0.0
var _sub: int = 0
var _sub_t: float = 0.0
var _flash: float = 0.0
var _facing: int = -1
var _contact_cd: float = 0.0
var _hit_area: Area2D
var _intro_t: float = 0.0
var _phase_broken: bool = false
var _gravity: float = 980.0
var _home_x: float = 0.0


func _ready() -> void:
	add_to_group("enemies")
	add_to_group("boss")
	_home_x = global_position.x
	label = I18n.t("boss.%d" % clampi(boss_index, 0, 6))
	max_hp = 22.0 + boss_index * 3.5
	hp = max_hp
	collision_layer = 4
	collision_mask = 1
	motion_mode = CharacterBody2D.MOTION_MODE_GROUNDED
	z_index = 2

	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(34, 46)
	shape.shape = rect
	shape.position = Vector2(0, -23)
	add_child(shape)

	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = _frames()
	_sprite.centered = false
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_sprite.play()
	add_child(_sprite)
	var tex := _sprite.sprite_frames.get_frame_texture("default", 0)
	if tex:
		_sprite_w = tex.get_width()
		_sprite_h = tex.get_height()
	_sprite.offset = Vector2(-_sprite_w * 0.5, -_sprite_h)

	_hit_area = Area2D.new()
	_hit_area.collision_layer = 0
	_hit_area.collision_mask = 2
	var hs := CollisionShape2D.new()
	var hr := RectangleShape2D.new()
	hr.size = Vector2(40, 50)
	hs.shape = hr
	hs.position = Vector2(0, -25)
	_hit_area.add_child(hs)
	add_child(_hit_area)
	_hit_area.body_entered.connect(_on_touch)

	health_changed.emit(1.0, label)


func _frames() -> SpriteFrames:
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	sf.add_animation("default")
	var base := "res://assets/sprites/%s" % SPRITES[clampi(boss_index, 0, SPRITES.size() - 1)]
	for i in 2:
		var p := "%s_%d.png" % [base, i]
		if ResourceLoader.exists(p):
			sf.add_frame("default", load(p))
		elif ResourceLoader.exists(base + ".png"):
			sf.add_frame("default", load(base + ".png"))
	sf.set_animation_speed("default", 3.0)
	sf.set_animation_loop("default", true)
	return sf


func is_dead() -> bool:
	return _dead


func hp_ratio() -> float:
	return clampf(hp / max_hp, 0.0, 1.0)


func take_hit(amount: float, from: Vector2, _knockback: float = 0.0) -> void:
	if _dead:
		return
	hp -= amount
	_flash = 0.1
	health_changed.emit(hp_ratio(), label)
	AudioDirector.sfx("hit", 0.1, -6.0)
	if hp <= 0.0:
		_die()
		return
	var ratio := hp_ratio()
	if phase == 1 and ratio < 0.62:
		phase = 2
		_cooldown = 0.6
		_break_phase()
	elif phase == 2 and ratio < 0.3:
		phase = 3
		_cooldown = 0.5
		_break_phase()


func _break_phase() -> void:
	AudioDirector.sfx("boss_roar", 0.05, -3.0)
	if level and level.camera:
		CameraShake.shake(level.camera, 0.6, 3.0)
	_attack = ""
	_at = 0.0
	# estallido de furia: pequeños proyectiles en cruz
	for i in 8:
		var dir := Vector2(cos(TAU * i / 8.0), sin(TAU * i / 8.0))
		Projectile.spawn(get_parent(), global_position + Vector2(0, -30), dir * 90.0,
				0.5, Color(0.9, 0.45, 0.3))


func stun(_t: float) -> void:
	pass


func _on_touch(body: Node) -> void:
	if _dead or _contact_cd > 0.0 or not active:
		return
	if body is Player:
		body.take_damage(1.0, global_position)
		_contact_cd = 1.0


func _physics_process(delta: float) -> void:
	if _dead:
		return
	_flash = maxf(0.0, _flash - delta)
	_contact_cd = maxf(0.0, _contact_cd - delta)
	_sprite.modulate = Color(2.4, 2.4, 2.4) if _flash > 0.0 else Color.WHITE
	_sprite.flip_h = _facing < 0

	var player := level.player if level else null
	if player == null or not is_instance_valid(player):
		return

	if not active:
		if global_position.distance_to(player.global_position) < 230.0:
			_activate()
		else:
			return

	if _intro_t > 0.0:
		_intro_t -= delta
		return

	var dist := global_position.distance_to(player.global_position)
	_facing = 1 if player.global_position.x > global_position.x else -1

	if _attack == "":
		_cooldown -= delta
		# se acerca lentamente
		if absf(player.global_position.x - global_position.x) > 60.0:
			var dir := signf(player.global_position.x - global_position.x)
			velocity.x = move_toward(velocity.x, dir * (48.0 + phase * 14.0), 320.0 * delta)
		else:
			velocity.x = move_toward(velocity.x, 0.0, 400.0 * delta)
		if _cooldown <= 0.0:
			_pick_attack(dist, player)
	else:
		_run_attack(delta, player)

	# correa de arena: el guardián no abandona su cámara
	var off := global_position.x - _home_x
	if absf(off) > 176.0:
		velocity.x = -signf(off) * (70.0 + phase * 12.0)

	if not is_on_floor():
		velocity.y = minf(velocity.y + _gravity * delta, 500.0)
	move_and_slide()


func _activate() -> void:
	active = true
	_intro_t = 1.1
	AudioDirector.sfx("boss_roar", 0.03, -1.0)
	AudioDirector.start_boss_music()
	activated.emit()
	if level and level.camera:
		CameraShake.shake(level.camera, 0.7, 2.5)


func _pick_attack(dist: float, player: Player) -> void:
	var pool: Array = PATTERNS[clampi(boss_index, 0, PATTERNS.size() - 1)].duplicate()
	if phase >= 2 and not pool.has("summon") and boss_index in [1, 4, 6]:
		pool.append("summon")
	if dist < 70.0 and pool.has("slam"):
		_attack = "slam"
	else:
		_attack = pool[randi() % pool.size()]
	_at = 0.0
	_sub = 0
	_sub_t = 0.0


func _run_attack(delta: float, player: Player) -> void:
	_at += delta
	match _attack:
		"volley":
			if _at > 0.3 and _sub < 3 + phase:
				_sub_t -= delta
				if _sub_t <= 0.0:
					_sub_t = 0.18
					_sub += 1
					var base := (player.global_position + Vector2(0, -18) - global_position).normalized()
					var ang := randf_range(-0.22, 0.22)
					var dir := base.rotated(ang)
					Projectile.spawn(get_parent(), global_position + Vector2(0, -40),
							dir * (120.0 + phase * 22.0), 1.0, Color(0.75, 0.4, 0.95))
					AudioDirector.sfx("swing", 0.2, -10.0)
			if _at > 1.2 + 0.3 * phase:
				_end_attack()
		"rain":
			if _at > 0.4 and _sub < 5 + phase:
				_sub_t -= delta
				if _sub_t <= 0.0:
					_sub_t = 0.22
					_sub += 1
					var x := player.global_position.x + randf_range(-90.0, 90.0)
					Projectile.spawn(get_parent(), Vector2(x, global_position.y - 140.0),
							Vector2(randf_range(-10, 10), 130.0), 1.0, Color(0.6, 0.8, 0.6))
			if _at > 1.8 + 0.2 * phase:
				_end_attack()
		"slam":
			if _sub == 0:
				_sub = 1
				var dir := signf(player.global_position.x - global_position.x)
				velocity = Vector2(dir * 190.0, -230.0)
			if _sub == 1 and _at > 0.35 and is_on_floor():
				_sub = 2
				_shockwave()
			if _at > 1.0:
				_end_attack()
		"charge":
			if _sub == 0:
				_sub = 1
				var dir := signf(player.global_position.x - global_position.x)
				velocity = Vector2(dir * (220.0 + phase * 30.0), 0)
				AudioDirector.sfx("dash", 0.1, -5.0)
			if _sub == 1:
				if is_on_wall() and _at > 0.2:
					_shockwave()
					_end_attack()
				elif _at > 0.62:
					_end_attack()
		"summon":
			if _at > 0.5 and _sub == 0:
				_sub = 1
				_summon()
			if _at > 1.4:
				_end_attack()
		"gaze":
			if _sub == 0:
				_sub = 1
				AudioDirector.sfx("whisper", 0.05, -1.0)
			# drena cordura y daña si estás cerca
			var d := global_position.distance_to(player.global_position)
			if d < 240.0:
				GameState.drain_clarity(delta * 12.0)
				if d < 90.0 and _contact_cd <= 0.0:
					player.take_damage(1.0, global_position)
			if _at > 2.2:
				_end_attack()


func _end_attack() -> void:
	_attack = ""
	_at = 0.0
	_sub = 0
	_cooldown = maxf(0.40, 1.35 - phase * 0.25)


func _shockwave() -> void:
	AudioDirector.sfx("hit", 0.05, -2.0)
	if level and level.camera:
		CameraShake.shake(level.camera, 0.35, 3.2)
	ScreamFX.spawn(get_parent(), global_position + Vector2(0, -12), 110.0)
	var player := level.player if level else null
	if player and is_instance_valid(player):
		if global_position.distance_to(player.global_position) < 90.0:
			player.take_damage(1.0, global_position)
	for i in 5:
		var dir := Vector2(-1 if i % 2 == 0 else 1, -0.4).normalized()
		Projectile.spawn(get_parent(), global_position + Vector2(0, -10),
				dir.rotated(randf_range(-0.5, 0.5)) * 110.0, 0.5, Color(0.8, 0.5, 0.35))


func _summon() -> void:
	var kinds := ["ahogado", "cultista", "polipo", "bestia", "migo"]
	var kind: String = kinds[clampi(boss_index, 0, kinds.size() - 1)]
	for i in 2:
		var e: Enemy = load("res://scripts/enemy.gd").new()
		e.kind = kind
		e.position = global_position + Vector2(randf_range(-60.0, 60.0), -10.0)
		e.level = level
		get_parent().add_child(e)
	AudioDirector.sfx("pickup", 0.1, -8.0)


func _die() -> void:
	_dead = true
	AudioDirector.stop_boss_music()
	AudioDirector.sfx("death", 0.02, -3.0)
	if level and level.camera:
		CameraShake.shake(level.camera, 1.1, 4.0)
	for i in 3:
		get_tree().create_timer(0.18 * i).timeout.connect(_burst)
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, 1.2)
	tw.tween_callback(func():
		defeated.emit()
		queue_free())


func _burst() -> void:
	if not is_inside_tree():
		return
	for i in 10:
		var dir := Vector2(cos(TAU * i / 10.0), sin(TAU * i / 10.0))
		Projectile.spawn(get_parent(), global_position + Vector2(0, -40), dir * 100.0,
				0.0, Color(0.9, 0.7, 0.5))
