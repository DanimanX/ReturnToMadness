extends CharacterBody2D
class_name Player
## El Testigo. Peso, filo y locura.

signal died
signal health_lost

enum State { IDLE, RUN, AIR, DASH, ATTACK, HURT, DEAD, VOICE }

const SPEED := 112.0
const ACCEL := 900.0
const FRICTION := 1250.0
const AIR_ACCEL := 620.0
const GRAVITY := 980.0
const MAX_FALL := 430.0
const JUMP_VELOCITY := -348.0
const COYOTE := 0.10
const JUMP_BUFFER := 0.12

const DASH_SPEED := 296.0
const DASH_TIME := 0.15
const DASH_COOLDOWN := 0.42

const ATK_DURATION := [0.30, 0.30, 0.38]
const ATK_ACTIVE_A := [0.07, 0.07, 0.09]
const ATK_ACTIVE_B := [0.19, 0.19, 0.24]
const COMBO_WINDOW := 0.26

const VOICE_COST := 18.0
const VOICE_RADIUS := 96.0
const VOICE_STUN := 2.2

const MAX_HP := 3

var state: State = State.IDLE
var facing: int = 1
var hp: int = MAX_HP
var level: Level = null

var _coyote: float = 0.0
var _buffer: float = 0.0
var _dash_t: float = 0.0
var _dash_cd: float = 0.0
var _invuln: float = 0.0
var _atk_t: float = 0.0
var _atk_index: int = 0
var _combo_t: float = 0.0
var _hit_this_swing: Dictionary = {}
var _voice_t: float = 0.0
var _hurt_t: float = 0.0
var _dead_t: float = 0.0
var _near_horror: float = 0.0
var _drift: float = 0.0
var _sprite: AnimatedSprite2D
var _hitbox: Area2D
var _hitbox_shape: CollisionShape2D
var _glow: Sprite2D
var _hazard_sensor: Area2D
var _anim_name: String = ""

const FRAME_SETS := {
	"idle": [4, 6.0, true],
	"run": [8, 12.0, true],
	"jump": [1, 8.0, false],
	"fall": [1, 8.0, false],
	"dash": [1, 8.0, false],
	"attack": [4, 14.0, false],
	"hurt": [1, 8.0, false],
	"death": [5, 8.0, false],
	"voice": [3, 9.0, false],
}


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	motion_mode = CharacterBody2D.MOTION_MODE_GROUNDED
	floor_snap_length = 4.0
	z_index = 2

	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(10, 26)
	shape.shape = rect
	shape.position = Vector2(0, -13)
	add_child(shape)

	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = _build_frames()
	_sprite.centered = false
	_sprite.offset = Vector2(-24, -46)
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(_sprite)
	_play("idle")

	_glow = Sprite2D.new()
	_glow.texture = load("res://assets/sprites/fx_glow_warm.png")
	_glow.position = Vector2(-9, -17)
	_glow.scale = Vector2(2.0, 2.0)
	_glow.modulate = Color(1.0, 0.74, 0.44, 0.55)
	_glow.z_index = -1
	var gm := CanvasItemMaterial.new()
	gm.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_glow.material = gm
	add_child(_glow)

	_hitbox = Area2D.new()
	_hitbox.collision_layer = 0
	_hitbox.collision_mask = 4
	_hitbox.monitoring = true
	_hitbox.monitorable = false
	_hitbox_shape = CollisionShape2D.new()
	var hr := RectangleShape2D.new()
	hr.size = Vector2(26, 24)
	_hitbox_shape.shape = hr
	_hitbox_shape.position = Vector2(14, -16)
	_hitbox.add_child(_hitbox_shape)
	_hitbox_shape.disabled = true
	add_child(_hitbox)

	_hazard_sensor = Area2D.new()
	_hazard_sensor.collision_layer = 0
	_hazard_sensor.collision_mask = 8
	_hazard_sensor.monitoring = true
	var hs := CollisionShape2D.new()
	var hsr := RectangleShape2D.new()
	hsr.size = Vector2(12, 26)
	hs.shape = hsr
	hs.position = Vector2(0, -13)
	_hazard_sensor.add_child(hs)
	add_child(_hazard_sensor)

	hp = GameState.health
	GameState.set_health(hp)


func _build_frames() -> SpriteFrames:
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	for name in FRAME_SETS.keys():
		var info: Array = FRAME_SETS[name]
		sf.add_animation(name)
		sf.set_animation_loop(name, info[2])
		sf.set_animation_speed(name, info[1])
		for i in int(info[0]):
			var path := "res://assets/sprites/testigo_%s_%d.png" % [name, i]
			if not ResourceLoader.exists(path):
				path = "res://assets/sprites/testigo_%s_0.png" % name
			if ResourceLoader.exists(path):
				sf.add_frame(name, load(path))
	return sf


func _play(name: String) -> void:
	if _anim_name == name:
		return
	_anim_name = name
	if _sprite.sprite_frames.has_animation(name):
		_sprite.play(name)


func is_dead() -> bool:
	return state == State.DEAD


func _physics_process(delta: float) -> void:
	_tick_timers(delta)
	if state == State.DEAD:
		velocity.x = move_toward(velocity.x, 0.0, FRICTION * delta)
		velocity.y = minf(velocity.y + GRAVITY * delta, MAX_FALL)
		move_and_slide()
		return

	var dir := Input.get_axis("move_left", "move_right")
	_drift = sin(Time.get_ticks_msec() * 0.001 * 1.7) * GameState.madness_ratio() * 12.0
	if GameState.tier() >= 4:
		dir = clampf(dir + _drift * 0.02, -1.0, 1.0)

	# gravedad
	if not is_on_floor():
		velocity.y = minf(velocity.y + GRAVITY * delta, MAX_FALL)

	match state:
		State.DASH:
			_process_dash(delta)
		State.ATTACK:
			_process_attack(delta, dir)
		State.VOICE:
			_process_voice(delta)
		State.HURT:
			_process_hurt(delta)
		_:
			_process_normal(delta, dir)

	move_and_slide()
	_update_facing(dir)
	_update_sprite(dir)
	_update_clarity(delta)
	_check_hazards()
	if global_position.y > 400:
		_die(true)


func _tick_timers(delta: float) -> void:
	_invuln = maxf(0.0, _invuln - delta)
	_dash_cd = maxf(0.0, _dash_cd - delta)
	_combo_t = maxf(0.0, _combo_t - delta)
	_coyote = maxf(0.0, _coyote - delta)
	if is_on_floor():
		_coyote = COYOTE
	_buffer = maxf(0.0, _buffer - delta)
	if Input.is_action_just_pressed("jump"):
		_buffer = JUMP_BUFFER
	if _combo_t <= 0.0 and state != State.ATTACK:
		_atk_index = 0
	if _invuln > 0.0:
		_sprite.modulate.a = 0.55 + 0.45 * sin(_invuln * 40.0)
	else:
		_sprite.modulate.a = 1.0
	# pulso del farol
	if _glow:
		_glow.modulate.a = 0.38 + sin(Time.get_ticks_msec() * 0.004) * 0.05


func _process_normal(delta: float, dir: float) -> void:
	if dir != 0.0:
		velocity.x = move_toward(velocity.x, dir * SPEED, ACCEL * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, FRICTION * delta)

	if _buffer > 0.0 and _coyote > 0.0:
		velocity.y = JUMP_VELOCITY
		_buffer = 0.0
		_coyote = 0.0
		AudioDirector.sfx("dash", 0.12, -14.0)
		_play("jump")
	if Input.is_action_just_released("jump") and velocity.y < -70.0:
		velocity.y *= 0.52

	if Input.is_action_pressed("attack"):
		_start_attack()
		return
	if Input.is_action_just_pressed("dash") and _dash_cd <= 0.0:
		_start_dash()
		return
	if Input.is_action_just_pressed("voice") and GameState.clarity >= VOICE_COST:
		_start_voice()
		return

	if is_on_floor():
		state = State.RUN if absf(velocity.x) > 6.0 else State.IDLE
	else:
		state = State.AIR


func _update_facing(dir: float) -> void:
	if state in [State.DASH, State.ATTACK, State.HURT, State.VOICE]:
		return
	if dir > 0.05:
		facing = 1
	elif dir < -0.05:
		facing = -1


func _update_sprite(dir: float) -> void:
	_sprite.flip_h = facing < 0
	# el hitbox sigue la mirada
	_hitbox_shape.position.x = 14.0 * facing
	match state:
		State.DEAD:
			_play("death")
		State.DASH:
			_play("dash")
		State.ATTACK:
			_play("attack")
		State.HURT:
			_play("hurt")
		State.VOICE:
			_play("voice")
		State.AIR:
			_play("fall" if velocity.y > 20.0 else "jump")
		State.RUN:
			_play("run")
		_:
			_play("idle")


# ------------------------------------------------------------------ ataque
func _start_attack() -> void:
	if state == State.ATTACK:
		# encadenar si estamos en la ventana
		if _combo_t > 0.0 and _atk_index < 2:
			_atk_index += 1
			_atk_t = 0.0
			_hit_this_swing.clear()
			_hitbox_shape.disabled = true
			AudioDirector.sfx("swing", 0.12, -5.0)
		return
	state = State.ATTACK
	_atk_t = 0.0
	_atk_index = 0
	_hit_this_swing.clear()
	_hitbox_shape.disabled = true
	AudioDirector.sfx("swing", 0.12, -5.0)


func _process_attack(delta: float, dir: float) -> void:
	_atk_t += delta
	velocity.x = move_toward(velocity.x, dir * SPEED * 0.32, ACCEL * delta)
	if Input.is_action_just_pressed("dash") and _dash_cd <= 0.0 and _atk_t > 0.10:
		_start_dash()
		return
	var i := clampi(_atk_index, 0, 2)
	var a: float = _atk_t - ATK_ACTIVE_A[i]
	var b: float = _atk_t - ATK_ACTIVE_B[i]
	if a >= 0.0 and b <= 0.0:
		_hitbox_shape.disabled = false
		_scan_hits(i)
	else:
		_hitbox_shape.disabled = true
	if _atk_t >= ATK_DURATION[i]:
		_hitbox_shape.disabled = true
		_combo_t = COMBO_WINDOW
		state = State.AIR if not is_on_floor() else State.IDLE
		if Input.is_action_pressed("attack") and _atk_index < 2:
			_atk_index += 1
			_atk_t = 0.0
			_hit_this_swing.clear()
			state = State.ATTACK


func _scan_hits(combo: int) -> void:
	for body in _hitbox.get_overlapping_bodies():
		if _hit_this_swing.has(body):
			continue
		if body.has_method("take_hit"):
			_hit_this_swing[body] = true
			var dmg := (1.0 + combo * 0.35) * GameState.damage_multiplier()
			body.take_hit(dmg, global_position, 130.0 + combo * 30.0)
			AudioDirector.sfx("hit", 0.14, -4.0)
			_hit_stop(0.045)


func _hit_stop(t: float) -> void:
	Engine.time_scale = 0.18
	var timer := get_tree().create_timer(t, true, false, true)
	timer.timeout.connect(func(): Engine.time_scale = 1.0)


# ------------------------------------------------------------------ dash
func _start_dash() -> void:
	state = State.DASH
	_dash_t = DASH_TIME
	_dash_cd = DASH_COOLDOWN
	_invuln = maxf(_invuln, DASH_TIME + 0.05)
	velocity = Vector2(facing * DASH_SPEED, 0)
	AudioDirector.sfx("dash", 0.08, -6.0)
	_afterimage()


func _process_dash(delta: float) -> void:
	_dash_t -= delta
	velocity = Vector2(facing * DASH_SPEED, 0)
	_afterimage()
	if _dash_t <= 0.0:
		velocity.x = facing * SPEED * 0.7
		state = State.AIR if not is_on_floor() else State.IDLE


func _afterimage() -> void:
	if not _sprite.sprite_frames.has_animation(_anim_name):
		return
	var ghost := Sprite2D.new()
	ghost.texture = _sprite.sprite_frames.get_frame_texture(_anim_name, _sprite.frame)
	ghost.centered = false
	ghost.offset = Vector2(-24 * (1 if facing > 0 else -1) - (24 if facing < 0 else 0), -46)
	ghost.flip_h = facing < 0
	ghost.modulate = Color(0.55, 0.75, 0.95, 0.35)
	ghost.global_position = Vector2(global_position.x, global_position.y)
	ghost.z_index = 1
	get_parent().add_child(ghost)
	var tw := ghost.create_tween()
	tw.tween_property(ghost, "modulate:a", 0.0, 0.22)
	tw.tween_callback(ghost.queue_free)


# ------------------------------------------------------------------ la voz
func _start_voice() -> void:
	state = State.VOICE
	_voice_t = 0.0
	GameState.drain_clarity(VOICE_COST)
	AudioDirector.sfx("voice", 0.05, -3.0)
	ScreamFX.spawn(get_parent(), global_position + Vector2(0, -18), VOICE_RADIUS)
	_shake(0.35, 3.0)
	var realm := GameState.madness_ratio()
	for e in get_tree().get_nodes_in_group("enemies"):
		if not is_instance_valid(e):
			continue
		var d: float = global_position.distance_to(e.global_position)
		if d <= VOICE_RADIUS + 20.0:
			if e.has_method("stun"):
				e.stun(VOICE_STUN * (1.0 + realm * 0.4))
			if e.has_method("take_hit"):
				e.take_hit(0.6 + realm * 0.8, global_position, 90.0)


func _process_voice(delta: float) -> void:
	_voice_t += delta
	velocity.x = move_toward(velocity.x, 0.0, FRICTION * delta)
	if _voice_t > 0.42:
		state = State.AIR if not is_on_floor() else State.IDLE


# ------------------------------------------------------------------ daño
func _process_hurt(delta: float) -> void:
	_hurt_t -= delta
	velocity.x = move_toward(velocity.x, 0.0, 500.0 * delta)
	if _hurt_t <= 0.0:
		state = State.AIR if not is_on_floor() else State.IDLE


func take_damage(amount: float, from: Vector2, ignore_iframes: bool = false) -> void:
	if state == State.DEAD:
		return
	if _invuln > 0.0 and not ignore_iframes:
		return
	hp -= 1
	GameState.set_health(hp)
	GameState.drain_clarity(14.0)
	_invuln = 0.95
	state = State.HURT
	_hurt_t = 0.28
	var dir := signf(global_position.x - from.x)
	if dir == 0.0:
		dir = -facing
	velocity = Vector2(dir * 150.0, -170.0)
	AudioDirector.sfx("hurt", 0.08, -3.0)
	_shake(0.25, 3.5)
	health_lost.emit()
	if hp <= 0:
		_die(false)


func _check_hazards() -> void:
	if _invuln > 0.0 or state == State.DEAD:
		return
	for a in _hazard_sensor.get_overlapping_areas():
		var dmg: float = a.get_meta("damage", 10.0)
		take_damage(dmg, a.global_position)
		return


func _update_clarity(delta: float) -> void:
	var nearest := 9999.0
	for e in get_tree().get_nodes_in_group("enemies"):
		if is_instance_valid(e) and e.has_method("is_dead") and not e.is_dead():
			nearest = minf(nearest, global_position.distance_to(e.global_position))
	_near_horror = clampf(1.0 - nearest / 190.0, 0.0, 1.0)
	if _near_horror > 0.05:
		GameState.drain_clarity(delta * (1.4 + GameState.madness * 0.55) * _near_horror)
	else:
		GameState.add_clarity(delta * 1.1)
	if GameState.clarity_empty():
		GameState.clarity = 35.0
		GameState.clarity_changed.emit(GameState.clarity)
		add_madness_on_break()


func add_madness_on_break() -> void:
	GameState.add_madness(0.05)
	take_damage(1.0, global_position + Vector2(0, -10), true)
	AudioDirector.sfx("whisper", 0.05, -2.0)


func _die(fell: bool) -> void:
	if state == State.DEAD:
		return
	state = State.DEAD
	hp = 0
	GameState.set_health(0)
	collision_mask = 0
	velocity = Vector2(0, -60) if not fell else Vector2.ZERO
	AudioDirector.sfx("death", 0.02, -2.0)
	_dead_t = 0.0
	died.emit()


func respawn(pos: Vector2) -> void:
	state = State.IDLE
	global_position = pos
	velocity = Vector2.ZERO
	hp = GameState.max_health
	GameState.set_health(hp)
	collision_mask = 1
	_invuln = 1.2
	_play("idle")


func heal_full() -> void:
	hp = GameState.max_health
	GameState.set_health(hp)


func _shake(duration: float, strength: float) -> void:
	if level and level.camera:
		CameraShake.shake(level.camera, duration, strength)
