extends Node2D
## Regreso a la Locura — flujo del juego: título, etapas, muerte, revelación, bucle.

enum Mode { TITLE, PLAY, PAUSE, DEAD, CLEAR, ENDING }

const TOTAL_STAGES := 7

var mode: Mode = Mode.TITLE
var world: Node2D
var hud: HUD
var fx: MadnessFX
var ui_layer: CanvasLayer
var overlay: Control
var level: Level
var player: Player

var _fade: ColorRect
var _fade_target: float = 0.0
var _fade_speed: float = 2.5
var _dead_t: float = 0.0
var _blink: float = 0.0
var _clear_text: String = ""
var _clear_title: String = ""
var _ending_step: int = 0
var _hint_t: float = 0.0
var _hide_prompt: bool = false
var _promo_card: bool = false
var _canvas_mod: CanvasModulate
var _title_tex: Texture2D
var _title_bg: Texture2D
var _has_save: bool = false


func _ready() -> void:
	randomize()
	process_mode = Node.PROCESS_MODE_ALWAYS

	world = Node2D.new()
	world.name = "World"
	add_child(world)

	_canvas_mod = CanvasModulate.new()
	_canvas_mod.color = Color(1.07, 1.07, 1.11)
	world.add_child(_canvas_mod)

	fx = MadnessFX.new()
	fx.world = world
	add_child(fx)

	hud = HUD.new()
	add_child(hud)
	fx.hud = hud
	hud.visible = false

	ui_layer = CanvasLayer.new()
	ui_layer.layer = 30
	add_child(ui_layer)

	overlay = Control.new()
	overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_layer.add_child(overlay)
	overlay.draw.connect(_draw_ui)

	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 1)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui_layer.add_child(_fade)

	_title_tex = load("res://assets/ui/title.png") if ResourceLoader.exists("res://assets/ui/title.png") else null
	_title_bg = load("res://assets/ui/title_bg.png") if ResourceLoader.exists("res://assets/ui/title_bg.png") else null

	AudioDirector.play_ambience(5)
	I18n.language_changed.connect(func(_c):
		if overlay:
			overlay.queue_redraw()
		if hud:
			hud.refresh())
	_has_save = GameState.has_save()
	_enter_title()

	if "--smoke" in OS.get_cmdline_user_args():
		var smoke: Node = load("res://scripts/smoke.gd").new()
		smoke.name = "Smoke"
		smoke.main = self
		add_child(smoke)


# ------------------------------------------------------------------ flujo
func _enter_title() -> void:
	mode = Mode.TITLE
	hud.visible = false
	_clear_world()
	_fade_to(0.0, 1.4)


func _start_run() -> void:
	GameState.reset_run()
	_load_stage(0)


func _load_stage(index: int) -> void:
	_clear_world()
	var data: Dictionary = StageData.STAGES[clampi(index, 0, StageData.STAGES.size() - 1)]
	level = Level.new()
	level.name = "Level"
	world.add_child(level)
	level.build(data, index)

	player = Player.new()
	player.name = "Player"
	player.level = level
	level.entities.add_child(player)
	player.global_position = level.spawn_point
	player.hp = GameState.max_health
	player.died.connect(_on_player_died)
	player.health_lost.connect(_on_player_hurt)
	level.attach_player(player)
	level.gate_reached.connect(_on_gate)
	level.checkpoint_activated.connect(_on_checkpoint)
	level.lore_collected.connect(_on_lore)
	level.boss_started.connect(_on_boss_started)
	level.boss_defeated.connect(_on_boss_defeated)

	hud.visible = true
	hud.clear_transient()
	var skey := String(data.get("key", ""))
	hud.show_stage_title(I18n.t("stage.%s.name" % skey),
			I18n.t("stage.%s.subtitle" % skey), I18n.t("stage.%s.intro" % skey))
	hud.clear_boss()
	AudioDirector.play_ambience(index)
	AudioDirector.stop_boss_music()
	mode = Mode.PLAY
	_fade_to(0.0, 0.9)
	_hint_t = 7.0


func _clear_world() -> void:
	for c in world.get_children():
		if c == _canvas_mod:
			continue
		c.queue_free()
	# los queue_free se aplican al final del frame; quitamos del árbol ya
	for c in world.get_children():
		if c == _canvas_mod:
			continue
		world.remove_child(c)
	level = null
	player = null


func _on_checkpoint(_pos: Vector2) -> void:
	GameState.save_game()


func _on_lore(text: String) -> void:
	if text != "":
		hud.show_lore(text)


func _on_player_hurt() -> void:
	fx.trigger_hurt()
	AudioDirector.sfx("whisper", 0.1, -18.0)


func _on_boss_started(boss: Node) -> void:
	hud.set_boss(boss)
	if boss.has_signal("health_changed"):
		boss.health_changed.connect(func(_r, _l): hud.set_boss(boss))


func _on_boss_defeated() -> void:
	hud.clear_boss()
	if player:
		player.heal_full()
	GameState.add_clarity(30.0)


func _on_player_died() -> void:
	if mode != Mode.PLAY:
		return
	mode = Mode.DEAD
	_dead_t = 0.0
	GameState.register_death()
	fx.trigger_hurt()
	_fade_to(0.35, 1.2)
	AudioDirector.stop_boss_music()
	hud.clear_boss()


func _respawn() -> void:
	var pos: Vector2 = level.active_checkpoint + Vector2(0, -2)
	player.respawn(pos)
	player.hp = GameState.max_health
	GameState.set_health(GameState.max_health)
	GameState.clarity = 60.0
	GameState.clarity_changed.emit(GameState.clarity)
	level.camera.reset_smoothing()
	mode = Mode.PLAY
	_fade_to(0.0, 0.8)
	AudioDirector.play_ambience(GameState.stage_index)
	if level.boss and is_instance_valid(level.boss) and level.boss.active and not level.boss.is_dead():
		hud.set_boss(level.boss)
		AudioDirector.start_boss_music()


func _on_gate() -> void:
	if mode != Mode.PLAY:
		return
	if level.boss != null and is_instance_valid(level.boss) and not level.boss.is_dead():
		hud.whisper(I18n.t("ui.seal_breathes"))
		return
	_complete_stage()


func _complete_stage() -> void:
	mode = Mode.CLEAR
	_promo_card = false
	GameState.complete_stage()
	GameState.save_game()
	var data: Dictionary = StageData.STAGES[GameState.stage_index]
	var skey := String(data.get("key", ""))
	_clear_title = I18n.t("stage.%s.name" % skey)
	_clear_text = I18n.t("stage.%s.revelation" % skey)
	AudioDirector.stop_boss_music()
	AudioDirector.stop_ambience(2.0)
	_fade_to(0.55, 1.6)
	GameState.stage_index += 1
	if GameState.stage_index >= TOTAL_STAGES:
		_ending_step = 0


func _next_after_clear() -> void:
	if GameState.stage_index >= TOTAL_STAGES:
		mode = Mode.ENDING
		_ending_step = 1
		_clear_title = I18n.t("end.title")
		_clear_text = I18n.t("end.body")
		_fade_to(0.55, 1.4)
	else:
		_load_stage(GameState.stage_index)


func _draw_ui() -> void:
	var vp := Vector2(480, 270)
	match mode:
		Mode.TITLE:
			_draw_title(vp)
		Mode.CLEAR:
			_draw_clear(vp, false)
		Mode.ENDING:
			_draw_clear(vp, true)
		Mode.PAUSE:
			_draw_pause(vp)
		Mode.DEAD:
			_draw_dead(vp)
		_:
			if _hint_t > 0.0 and not (level and level.boss and is_instance_valid(level.boss) and level.boss.active):
				var a := clampf(_hint_t / 2.0, 0.0, 1.0) * 0.8
				overlay.draw_rect(Rect2(0, 236, vp.x, 16), Color(0.02, 0.02, 0.03, 0.55 * a))
				PixelFont.draw_centered(overlay, vp.x * 0.5, 241, I18n.t("ui.hint"),
						1, Color(0.72, 0.74, 0.66, a), false)


func _draw_title(vp: Vector2) -> void:
	if _title_bg:
		overlay.draw_texture(_title_bg, Vector2.ZERO)
	else:
		overlay.draw_rect(Rect2(0, 0, vp.x, vp.y), Color(0.02, 0.02, 0.03, 0.9))
	# banda oscura con caída suave: el texto se lee sin cortar la imagen
	var steps := 14
	for i in steps:
		var y := 6.0 + i * 11.5
		var a := 0.46 * (1.0 - float(i) / float(steps)) + 0.06
		overlay.draw_rect(Rect2(0, y, vp.x, 12.0), Color(0.02, 0.02, 0.03, a))

	# el título se dibuja con la tipografía del juego: existe en cinco idiomas
	var title := I18n.t("app.title")
	var ts := 3 if PixelFont.measure(title, 3).x <= vp.x - 36 else 2
	PixelFont.draw_centered(overlay, vp.x * 0.5, 26, title, ts, Color(0.90, 0.86, 0.74), true)

	PixelFont.draw_centered(overlay, vp.x * 0.5, 74, I18n.t("app.tagline1"), 1,
			Color(0.66, 0.70, 0.63))
	PixelFont.draw_centered(overlay, vp.x * 0.5, 87, I18n.t("app.tagline2"), 1,
			Color(0.50, 0.57, 0.52))

	var a := 0.45 + 0.55 * (0.5 + 0.5 * sin(_blink * 3.0))
	var prompt := I18n.t("app.press_continue") if _has_save else I18n.t("app.press_enter")
	PixelFont.draw_centered(overlay, vp.x * 0.5, 116, prompt, 1, Color(0.90, 0.82, 0.58, a))
	if _has_save:
		PixelFont.draw_centered(overlay, vp.x * 0.5, 129, I18n.t("app.reset_hint"), 1,
				Color(0.48, 0.50, 0.46))

	_draw_language_picker(vp, 252.0, 8.0)

	var credit := I18n.t("app.credit")
	var cw := PixelFont.measure(credit, 1).x
	PixelFont.draw(overlay, Vector2(vp.x - cw - 6, 258), credit, 1, Color(0.34, 0.34, 0.33), false)


## Tarjeta de texto para el video promocional (sin prompt de teclado).
func promo_card(title: String, body: String) -> void:
	mode = Mode.CLEAR
	_hide_prompt = true
	_promo_card = true
	_clear_title = title
	_clear_text = body
	_clear_title = title
	hud.visible = false
	fx.trigger_voice()
	_fade_to(0.42, 1.2)


func _draw_language_picker(vp: Vector2, y_center: float, x_left: float = -1.0) -> void:
	var label := "%s   < %s >" % [I18n.t("ui.lang_label"), I18n.native_name()]
	var w := PixelFont.measure(label, 1).x
	var x := x_left if x_left >= 0.0 else (vp.x - w) * 0.5
	var y := y_center - 4.0
	overlay.draw_rect(Rect2(x - 5, y, w + 10, 13), Color(0.04, 0.04, 0.05, 0.62))
	PixelFont.draw(overlay, Vector2(x, y + 3), label, 1, Color(0.76, 0.78, 0.68), false)


func _draw_clear(vp: Vector2, ending: bool) -> void:
	overlay.draw_rect(Rect2(0, 0, vp.x, vp.y), Color(0.02, 0.015, 0.02, 0.86))
	var y := 26.0 if _promo_card else 54.0
	PixelFont.draw_centered(overlay, vp.x * 0.5, y, _clear_title, 2, Color(0.90, 0.84, 0.68), true)
	y += 32.0 if _promo_card else 34.0
	if not _promo_card:
		PixelFont.draw_centered(overlay, vp.x * 0.5, y, I18n.t("ui.revelation"), 1,
				Color(0.50, 0.46, 0.36))
		y += 20.0
	var size := 2 if _promo_card else 1
	var max_w := 400 if _promo_card else 340
	var lines := _wrap(_clear_text, max_w, size)
	for line in lines:
		PixelFont.draw_centered(overlay, vp.x * 0.5, y, line, size, Color(0.82, 0.80, 0.72))
		y += 12.0 if size == 1 else 18.5
	y += 18
	if not _promo_card:
		PixelFont.draw_centered(overlay, vp.x * 0.5, y,
				"%s %d / 7" % [I18n.t("ui.madness"), GameState.tier()], 1, Color(0.66, 0.48, 0.72))
	var a := 0.45 + 0.55 * (0.5 + 0.5 * sin(_blink * 3.0))
	if not _hide_prompt:
		var prompt := I18n.t("end.prompt") if ending else I18n.t("end.next")
		PixelFont.draw_centered(overlay, vp.x * 0.5, 240, prompt, 1, Color(0.86, 0.78, 0.58, a))


func _draw_pause(vp: Vector2) -> void:
	overlay.draw_rect(Rect2(0, 0, vp.x, vp.y), Color(0.02, 0.02, 0.03, 0.82))
	PixelFont.draw_centered(overlay, vp.x * 0.5, 70, I18n.t("ui.paused"), 3, Color(0.88, 0.82, 0.68))
	var lines := [
		I18n.t("ui.ctrl_move"), I18n.t("ui.ctrl_jump"), I18n.t("ui.ctrl_attack"),
		I18n.t("ui.ctrl_dash"), I18n.t("ui.ctrl_voice"), I18n.t("ui.ctrl_pause"),
	]
	var y := 120.0
	for l in lines:
		PixelFont.draw_centered(overlay, vp.x * 0.5, y, l, 1, Color(0.74, 0.72, 0.64))
		y += 13
	PixelFont.draw_centered(overlay, vp.x * 0.5, 224,
			I18n.t("ui.resume"), 1, Color(0.56, 0.56, 0.50))
	var lang := "%s: %s   [ < > ]" % [I18n.t("ui.lang_label"), I18n.native_name()]
	PixelFont.draw_centered(overlay, vp.x * 0.5, 240, lang, 1, Color(0.52, 0.56, 0.52))


func _draw_dead(vp: Vector2) -> void:
	var a := clampf(_dead_t / 0.6, 0.0, 1.0)
	PixelFont.draw_centered(overlay, vp.x * 0.5, 120,
			I18n.t("death.title"), 2, Color(0.72, 0.36, 0.34, a))
	PixelFont.draw_centered(overlay, vp.x * 0.5, 146,
			"%s %d / 7  ·  %s %d" % [I18n.t("death.madness"), GameState.tier(),
			I18n.t("death.deaths"), GameState.deaths], 1, Color(0.60, 0.52, 0.52, a))


func _wrap(text: String, width: int, size: int) -> PackedStringArray:
	return PixelFont._wrap(text, PixelFont.char_width(size), width)


# ------------------------------------------------------------------ input
func _unhandled_input(event: InputEvent) -> void:
	# --- selector de idioma: flechas en título y en pausa ---
	if mode == Mode.TITLE or mode == Mode.PAUSE:
		if event.is_action_pressed("ui_left"):
			I18n.next(-1)
			AudioDirector.sfx("menu", 0.0, -10.0)
			overlay.queue_redraw()
			hud.refresh()
			return
		if event.is_action_pressed("ui_right"):
			I18n.next(1)
			AudioDirector.sfx("menu", 0.0, -10.0)
			overlay.queue_redraw()
			hud.refresh()
			return

	if event.is_action_pressed("pause") and mode == Mode.PLAY:
		mode = Mode.PAUSE
		get_tree().paused = true
		AudioDirector.sfx("menu", 0.0, -8.0)
		return
	if event.is_action_pressed("pause") and mode == Mode.PAUSE:
		mode = Mode.PLAY
		get_tree().paused = false
		return

	if mode == Mode.TITLE and event is InputEventKey and event.pressed \
			and (event as InputEventKey).keycode == KEY_DELETE:
		GameState.wipe_save()
		_has_save = false
		AudioDirector.sfx("menu", 0.0, -6.0)
		return
	if not event.is_action_pressed("confirm"):
		return
	match mode:
		Mode.TITLE:
			AudioDirector.sfx("menu", 0.0, -6.0)
			_fade_to(1.0, 0.5)
			await get_tree().create_timer(0.5).timeout
			if _has_save and GameState.load_game():
				_load_stage(GameState.stage_index)
			else:
				_start_run()
		Mode.CLEAR:
			AudioDirector.sfx("menu", 0.0, -6.0)
			_fade_to(1.0, 0.45)
			await get_tree().create_timer(0.45).timeout
			_next_after_clear()
		Mode.ENDING:
			AudioDirector.sfx("menu", 0.0, -6.0)
			_fade_to(1.0, 0.6)
			await get_tree().create_timer(0.6).timeout
			_loop_again()


func _loop_again() -> void:
	GameState.echo_loop += 1
	GameState.stage_index = 0
	GameState.madness = maxf(GameState.madness, 4.0)
	GameState.start_stage(0)
	_load_stage(0)
	AudioDirector.play_ambience(0)


# ------------------------------------------------------------------ frame
func _process(delta: float) -> void:
	_blink += delta
	if _hint_t > 0.0:
		_hint_t -= delta
	var a := _fade.color.a
	if absf(a - _fade_target) > 0.001:
		a = move_toward(a, _fade_target, _fade_speed * delta)
		_fade.color.a = a

	match mode:
		Mode.DEAD:
			_dead_t += delta
			if _dead_t > 2.0:
				_respawn()
		Mode.TITLE, Mode.CLEAR, Mode.ENDING, Mode.PAUSE:
			overlay.queue_redraw()
		Mode.PLAY:
			if _hint_t > 0.0:
				overlay.queue_redraw()


func _fade_to(value: float, speed: float) -> void:
	_fade_target = value
	_fade_speed = maxf(0.05, speed)
