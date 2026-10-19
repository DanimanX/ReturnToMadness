extends Node
## Arnés de verificación y capturas. Solo se activa con argumentos:
##   godot --path . -- --smoke                       (capturas guiadas)
##   godot --path . -- --smoke --traverse [--invuln] [--stage=N]
##   godot --path . -- --smoke --bosstest --stage=N

var main: Node
var shots_dir := "/tmp/shots"
var failures: Array[String] = []

var t: float = 0.0
var step: int = 0
var _t_step: float = -1.0

var _bot: Node = null
var _saved_at_start: bool = false

# modo recorrido
var traversing: bool = false
var boss_mode: bool = false
var lang_mode: bool = false
var promo_mode: bool = false
var trav_only: int = -1
var invulnerable: bool = false
var trav_stage: int = 0
var trav_t: float = 0.0
var trav_results: Array = []
var _gate_hit: bool = false
var _finishing: bool = false
var _last_log: float = 0.0
var _boss_dead: bool = false
var _boss_dead_at: float = -1.0
var _clear_seen: bool = false
var _gate_sent: bool = false
var _tested_stage: int = 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	DirAccess.make_dir_recursive_absolute(shots_dir)
	print("[smoke] inicio")
	_saved_at_start = GameState.has_save()
	print("[smoke] guardado=%s" % str(_saved_at_start))
	if _saved_at_start and "--wipe" in OS.get_cmdline_user_args():
		GameState.wipe_save()
		_saved_at_start = false
	var args := OS.get_cmdline_user_args()
	for a in args:
		if a.begins_with("--stage="):
			trav_only = int(a.split("=")[1]) - 1
		if a == "--invuln":
			invulnerable = true
	if "--promo" in args:
		_promo_start()
		return
	if "--langtest" in args:
		_lang_test()
		return
	if "--checkload" in args:
		var ok := GameState.load_game()
		log_line("cargar partida: %s etapa=%d locura=%.2f cirios=%d" % [
			str(ok), GameState.stage_index + 1, GameState.madness, GameState.health])
		if not ok:
			fail("no se pudo cargar la partida guardada")
		_finish()
		return
	if "--bosstest" in args:
		_start_after_ready(1)
	elif "--traverse" in args:
		_start_after_ready(2)


func _start_after_ready(mode: int) -> void:
	await get_tree().process_frame
	if mode == 1:
		begin_boss_test(maxi(0, trav_only))
	else:
		main._start_run()
		begin_traverse()


func log_line(msg: String) -> void:
	print("[smoke] %s" % msg)


func fail(msg: String) -> void:
	failures.append(msg)
	print("[smoke] FALLO: %s" % msg)


func shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := "%s/%s.png" % [shots_dir, name]
	if img.save_png(path) != OK:
		fail("no se pudo guardar %s" % path)
	else:
		log_line("captura %s  %dx%d" % [name, img.get_width(), img.get_height()])


func _make_bot() -> void:
	if _bot and is_instance_valid(_bot):
		_bot.queue_free()
	_bot = load("res://scripts/bot.gd").new()
	add_child(_bot)
	_bot.setup(main.level, main.player)


func _lang_test() -> void:
	lang_mode = true
	await get_tree().process_frame
	main._start_run()
	await get_tree().create_timer(0.4).timeout
	for lang in I18n.LANGS:
		I18n.set_language(lang, false)
		main.hud.clear_transient()
		var skey := String(StageData.STAGES[0]["key"])
		main.hud.show_stage_title(I18n.t("stage.%s.name" % skey),
				I18n.t("stage.%s.subtitle" % skey), I18n.t("stage.%s.intro" % skey))
		await get_tree().create_timer(0.5).timeout
		await shot("lang_%s" % lang)
		log_line("%s · %s · %s" % [lang, I18n.t("app.press_enter"), I18n.t("ui.clarity")])
	main._enter_title()
	await get_tree().create_timer(0.5).timeout
	for lang in ["fr", "it", "pt"]:
		I18n.set_language(lang, false)
		await get_tree().create_timer(0.35).timeout
		await shot("titulo_%s" % lang)
	_finish()


# =================================================================== promo
# Secuencia lineal pensada para grabarse con --write-movie.
const PROMO := [
	{"kind": "title", "dur": 4.0},
	{"kind": "play", "stage": 0, "dur": 6.5, "at": 0.22, "madness": 0.6},
	{"kind": "play", "stage": 1, "dur": 5.0, "at": 0.30, "madness": 1.6},
	{"kind": "play", "stage": 2, "dur": 5.0, "at": 0.34, "madness": 2.6},
	{"kind": "play", "stage": 4, "dur": 5.0, "at": 0.40, "madness": 4.6},
	{"kind": "play", "stage": 5, "dur": 4.5, "at": 0.45, "madness": 6.0},
	{"kind": "boss", "stage": 0, "dur": 6.5},
	{"kind": "boss", "stage": 6, "dur": 7.5},
	{"kind": "card", "dur": 6.0},
]

var _promo_i: int = -1
var _promo_t: float = 0.0
var _promo_frames: int = 0


func _promo_start() -> void:
	promo_mode = true
	trav_only = 0
	I18n.set_language("es", false)
	main.hud.quiet = true
	main._enter_title()
	_promo_advance()


func _promo_advance() -> void:
	_promo_i += 1
	_promo_t = 0.0
	if _promo_i >= PROMO.size():
		# deja unos frames de negro antes de cortar
		await get_tree().create_timer(1.0).timeout
		log_line("promo grabado")
		get_tree().quit(0)
		return
	var beat: Dictionary = PROMO[_promo_i]
	var kind := String(beat["kind"])
	# el frame es la unidad de tiempo del grabador: sirve para alinear el audio
	log_line("promo %d/%d : %s @%.2fs" % [_promo_i + 1, PROMO.size(), kind, _promo_frames / 30.0])
	match kind:
		"title":
			main._has_save = false
			main._enter_title()
			main._fade_to(0.0, 1.0)
		"play":
			_promo_play(int(beat["stage"]), float(beat["at"]), float(beat["madness"]))
		"boss":
			_promo_boss(int(beat["stage"]))
		"card":
			main.promo_card("REGRESO A LA LOCURA",
					"Un juego de DanimanX\n\nSiete descensos.\nUna sola cordura.\n\n"
					+ "Godot 4\nArte, audio y niveles generados\n\n"
					+ "ESPAÑOL · ENGLISH\nFRANÇAIS · PORTUGUÊS · ITALIANO")


func _promo_play(index: int, at: float, madness: float) -> void:
	GameState.madness = madness
	GameState.start_stage(index)
	main._load_stage(index)
	GameState.madness = madness
	var lvl = main.level
	var p = main.player
	p.global_position = Vector2(lvl.width_tiles * 16.0 * at, lvl.spawn_point.y)
	p.velocity = Vector2.ZERO
	p.hp = 4
	GameState.set_health(4)
	lvl.camera.reset_smoothing()
	_make_bot()
	main._hint_t = 0.0
	if _promo_i > 1:
		main.hud._title_t = 2.2
	main._fade_to(0.0, 0.9)


func _promo_boss(index: int) -> void:
	GameState.madness = float(index) + 0.8
	GameState.start_stage(index)
	main._load_stage(index)
	var lvl = main.level
	var p = main.player
	if lvl.boss == null:
		_promo_advance()
		return
	p.global_position = lvl.boss.global_position + Vector2(-104, -2)
	p.hp = 4
	GameState.set_health(4)
	lvl.camera.reset_smoothing()
	_make_bot()
	main._hint_t = 0.0
	main.hud._title_t = 0.0
	main._fade_to(0.0, 0.9)


func _process_promo(delta: float) -> void:
	if _promo_i < 0 or _promo_i >= PROMO.size():
		return
	_promo_frames += 1
	_promo_t += delta
	var beat: Dictionary = PROMO[_promo_i]
	var kind := String(beat["kind"])
	_promo_frame_camera(kind)
	# el jugador nunca muere en el promo: la toma se corta, no se reinicia
	if main.player and is_instance_valid(main.player):
		main.player.hp = 4
		GameState.set_health(4)
		main.player._invuln = 0.6
		GameState.clarity = maxf(GameState.clarity, 70.0)
	if kind == "boss" and main.level and main.level.boss and is_instance_valid(main.level.boss):
		var b = main.level.boss
		if absf(main.player.global_position.x - b.global_position.x) < 130.0:
			main.player.global_position.x = b.global_position.x - 150.0
		if b.is_dead():
			main.level.boss.queue_free()
			main.level.boss = null
	if _promo_t >= float(beat["dur"]):
		main._fade_to(1.0, 0.45)
		_promo_advance()


## Encuadre fijo para el promo: sin suavizado, centrado en lo que importa.
func _promo_frame_camera(kind: String) -> void:
	var lvl = main.level
	var p = main.player
	if lvl == null or p == null or lvl.camera == null:
		return
	var cam: Camera2D = lvl.camera
	cam.position_smoothing_enabled = false
	var target: Vector2 = p.global_position + Vector2(0, -44)
	if kind == "boss" and lvl.boss and is_instance_valid(lvl.boss):
		# retrato del guardián: la cámara lo encuadra a él, no al jugador
		target = lvl.boss.global_position + Vector2(0, -58)
	# respeta los límites del nivel para no enseñar el vacío
	target.x = clampf(target.x, 240.0, lvl.width_tiles * 16.0 - 240.0)
	target.y = clampf(target.y, 135.0, lvl.grid.size() * 16.0 - 135.0)
	cam.global_position = target


# =================================================================== capturas
func _process(delta: float) -> void:
	t += delta
	if promo_mode:
		_process_promo(delta)
		return
	if lang_mode:
		return
	if boss_mode:
		_process_boss_test(delta)
		return
	if traversing:
		_process_traverse(delta)
		return
	_process_showcase(delta)


func _wait(seconds: float) -> bool:
	if _t_step < 0.0:
		_t_step = t
	return t - _t_step >= seconds


func _next() -> void:
	step += 1
	_t_step = -1.0


func _process_showcase(delta: float) -> void:
	match step:
		0:
			if _wait(0.9):
				await shot("01_titulo")
				_next()
		1:
			if _wait(0.4):
				# probar el camino real de entrada: ENTER en el título
				var ev := InputEventKey.new()
				ev.keycode = KEY_ENTER
				ev.physical_keycode = KEY_ENTER
				ev.pressed = true
				Input.parse_input_event(ev)
				_next()
		2:
			if _wait(1.8):
				log_line("guardado presente al arrancar: %s" % str(_saved_at_start))
				if main.mode != main.Mode.PLAY:
					fail("ENTER en el título no inició la partida (modo=%d)" % main.mode)
				else:
					log_line("ENTER inició la partida correctamente")
				_make_bot()
				await shot("02_etapa1_inicio")
				_next()
		3:
			if _wait(4.5):
				await shot("03_etapa1_jugando")
				_next()
		4:
			if _wait(4.0):
				# mirar la locura alta sin combate encima: se detiene el bot
				if _bot and is_instance_valid(_bot):
					_bot.queue_free()
					_bot = null
				Input.action_release("move_right")
				GameState.madness = 6.2
				GameState.madness_changed.emit(6.2)
				main.hud.clear_transient()
				if main.player and main.level:
					main.player.global_position = main.level.spawn_point + Vector2(40, 0)
					main.player.velocity = Vector2.ZERO
					main.player.hp = 3
					GameState.set_health(3)
					GameState.clarity = 100.0
					GameState.clarity_changed.emit(100.0)
					main.level.camera.reset_smoothing()
				_next()
		5:
			if _wait(2.6):
				await shot("04_locura6")
				_next()
		6:
			if _wait(0.4):
				GameState.madness = 3.0
				GameState.start_stage(2)
				main._load_stage(2)
				_next()
		7:
			if _wait(0.5):
				_make_bot()
				_next()
		8:
			if _wait(5.0):
				await shot("05_etapa3_biblioteca")
				_next()
		9:
			if _wait(0.2):
				GameState.start_stage(6)
				main._load_stage(6)
				_next()
		10:
			if _wait(0.4):
				_make_bot()
				var lvl = main.level
				if lvl.boss:
					main.player.global_position = lvl.boss.global_position + Vector2(-80, -2)
					lvl.camera.reset_smoothing()
				_next()
		11:
			if _wait(2.6):
				await shot("06_cthulhu")
				_next()
		12:
			if _wait(1.0):
				_check_showcase()
				_finish()
				_next()
		_:
			pass


func _check_showcase() -> void:
	var lvl = main.level
	if lvl == null:
		fail("la etapa final no cargó")
		return
	if lvl.boss == null:
		fail("la etapa final no tiene jefe")
	log_line("estado final: locura=%.1f etapa=%d enemigos=%d" % [
		GameState.madness, GameState.stage_index + 1, lvl.enemies().size()])


# =================================================================== recorrido
func begin_traverse() -> void:
	traversing = true
	trav_stage = maxi(0, trav_only)
	trav_t = 0.0
	Engine.time_scale = 2.5
	_start_traverse_stage(trav_stage)


func _start_traverse_stage(i: int) -> void:
	GameState.madness = float(i) * 1.0
	GameState.start_stage(i)
	main._load_stage(i)
	_gate_hit = false
	trav_t = 0.0
	_make_bot()
	main.level.gate_reached.connect(func(): _gate_hit = true)
	main.player.died.connect(func():
		log_line("  MUERTE etapa %d en %s" % [
			trav_stage + 1, str(main.player.global_position.round())]))


func _process_traverse(delta: float) -> void:
	trav_t += delta
	_last_log += delta
	if _last_log > 8.0 and main.player:
		_last_log = 0.0
		var pp = main.player
		var lv = main.level
		log_line("  t=%.0fs x=%.0f (tile %d/%d) hp=%d" % [
			trav_t, pp.global_position.x, int(pp.global_position.x / 16), lv.width_tiles, pp.hp])
	var lvl = main.level
	if lvl == null or main.player == null:
		return
	var p = main.player
	if invulnerable:
		p.hp = GameState.max_health
		GameState.set_health(p.hp)
		GameState.clarity = 100.0
		p._invuln = 1.0   # invulnerabilidad real: sin aturdimiento
	var arena_x: float = lvl.width_tiles * 16.0 - 300.0
	if _gate_hit or p.global_position.x >= arena_x:
		_finish_traverse_stage(true)
		return
	if trav_t > 95.0:
		_finish_traverse_stage(false)
		return


func _finish_traverse_stage(ok: bool) -> void:
	if _finishing:
		return
	_finishing = true
	var lvl = main.level
	var p = main.player
	var dist := 0.0
	var pct := 0.0
	if lvl and p:
		dist = p.global_position.x
		pct = clampf(p.global_position.x / maxf(1.0, lvl.width_tiles * 16.0 - 120.0), 0.0, 1.0) * 100.0
	trav_results.append({"stage": trav_stage + 1, "ok": ok, "x": dist, "pct": pct})
	log_line("RECORRIDO etapa %d: %s  x=%.0f  avance=%.0f%%  t=%.1fs" % [
		trav_stage + 1, "ARENA" if ok else "NO LLEGÓ", dist, pct, trav_t])
	if not ok:
		fail("bot no terminó la etapa %d (avance %.0f%%)" % [trav_stage + 1, pct])
	trav_stage += 1
	_finishing = false
	if trav_only >= 0 and trav_stage > trav_only:
		Engine.time_scale = 1.0
		traversing = false
		log_line("RECORRIDO (etapa suelta) terminado")
		# sin ventana no hay frame_post_draw: hay que salir, no pasar a capturas
		_finish()
		return
	if trav_stage >= 7:
		Engine.time_scale = 1.0
		traversing = false
		log_line("RECORRIDO completado")
		return
	_start_traverse_stage(trav_stage)


# =================================================================== jefe
func begin_boss_test(index: int) -> void:
	_tested_stage = index
	boss_mode = true
	invulnerable = true
	Engine.time_scale = 2.0
	GameState.start_stage(index)
	main._load_stage(index)
	await get_tree().process_frame
	var lvl = main.level
	if lvl == null or lvl.boss == null:
		fail("etapa %d sin jefe" % (index + 1))
		_finish()
		return
	main.player.global_position = lvl.boss.global_position + Vector2(-70, -2)
	lvl.camera.reset_smoothing()
	lvl.boss.defeated.connect(func():
		_boss_dead = true
		log_line("JEFE %s DERROTADO" % lvl.boss.label))
	_make_bot()
	log_line("duelo: %s  vida=%.0f" % [lvl.boss.label, lvl.boss.max_hp])


func _process_boss_test(delta: float) -> void:
	trav_t += delta
	var lvl = main.level
	var p = main.player
	if lvl == null or p == null:
		return
	p.hp = GameState.max_health
	GameState.set_health(p.hp)
	GameState.clarity = 100.0
	p._invuln = 1.0
	var boss = lvl.boss
	if boss and is_instance_valid(boss) and not boss.is_dead():
		# el arnés mantiene al jugador en la arena: se prueba el combate, no el pathing
		var d: float = p.global_position.distance_to(boss.global_position)
		if d > 52.0 or absf(p.global_position.y - boss.global_position.y) > 26.0:
			var side := -1.0 if p.global_position.x < boss.global_position.x else 1.0
			var tx: float = boss.global_position.x + 26.0 * side
			tx = clampf(tx, 40.0, lvl.width_tiles * 16.0 - 40.0)
			p.global_position = Vector2(tx, boss.global_position.y - 2.0)
			p.velocity = Vector2.ZERO
	_last_log += delta
	if _last_log > 6.0:
		_last_log = 0.0
		log_line("    jefe=%s vida=%.0f%% jugador=%s estado=%d activo=%s dist=%.0f" % [
			str(boss.global_position.round()) if boss and is_instance_valid(boss) else "null",
			(boss.hp_ratio() * 100.0) if boss and is_instance_valid(boss) else -1.0,
			str(p.global_position.round()), p.state,
			str(boss.active) if boss and is_instance_valid(boss) else "-",
			p.global_position.distance_to(boss.global_position) if boss and is_instance_valid(boss) else -1.0])
	if _boss_dead and _boss_dead_at < 0.0:
		_boss_dead_at = trav_t
	if _boss_dead and not _gate_sent:
		_gate_sent = true
		p.global_position = lvl.gate_pos + Vector2(20, 64)
		log_line("  -> a la puerta")
	if main.mode == main.Mode.CLEAR:
		_clear_seen = true
	if trav_t > 90.0 or (_boss_dead_at >= 0.0 and trav_t - _boss_dead_at > 4.0):
		var label := "OK" if (_boss_dead and _clear_seen) else \
				("JEFE OK, PUERTA NO" if _boss_dead else "NO MATÓ AL JEFE")
		log_line("DUELO etapa %d: %s  t=%.1fs  locura=%.1f" % [
			_tested_stage + 1, label, trav_t, GameState.madness])
		if not _clear_seen:
			fail("etapa %d: no se completó el ciclo jefe->puerta" % (_tested_stage + 1))
		_finish()


# =================================================================== cierre
func _finish() -> void:
	Engine.time_scale = 1.0
	if failures.is_empty():
		log_line("RESULTADO: OK")
	else:
		log_line("RESULTADO: %d fallos" % failures.size())
		for f in failures:
			log_line("  - %s" % f)
	get_tree().quit(0 if failures.is_empty() else 1)
