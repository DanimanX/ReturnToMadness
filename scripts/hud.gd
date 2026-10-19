extends CanvasLayer
class_name HUD
## Interfaz diegética: cirios, cordura, locura, jefe y susurros.

var root: Control
var _candle_full: Texture2D
var _candle_empty: Texture2D
var _eye: Texture2D

var _boss: Node = null
var _boss_label := ""
var _boss_ratio := 0.0

var _whispers: Array = []        # [{text, t, life, color}]
var _lore: Array = []            # [{text, t, life}]
var _stage_title := ""
var _title_t := 0.0
var _subtitle := ""
var _intro := ""
var _flicker := 0.0
var quiet: bool = false


func _ready() -> void:
	layer = 20
	_candle_full = _tex("res://assets/ui/ui_candle_full.png")
	_candle_empty = _tex("res://assets/ui/ui_candle_empty.png")
	_eye = _tex("res://assets/ui/ui_eye.png")
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	root.draw.connect(_on_draw)
	GameState.clarity_changed.connect(func(_v): _redraw())
	GameState.madness_changed.connect(func(_v): _redraw())
	I18n.language_changed.connect(func(_c): _redraw())


func _tex(path: String) -> Texture2D:
	return load(path) if ResourceLoader.exists(path) else null


func _redraw() -> void:
	if root:
		root.queue_redraw()


## Para el código externo: refresca sin exponer el nodo interno.
func refresh() -> void:
	_redraw()


func clear_transient() -> void:
	_whispers.clear()
	_lore.clear()
	_boss = null
	_redraw()


func show_stage_title(title: String, subtitle: String, intro: String = "") -> void:
	_stage_title = title
	_subtitle = subtitle
	_intro = intro
	_title_t = 5.4
	_redraw()


func whisper(text: String) -> void:
	if quiet:
		return
	_whispers.append({"text": text, "t": 0.0, "life": 4.5,
			"color": Color(0.72, 0.86, 0.74, 0.0)})
	if _whispers.size() > 4:
		_whispers.pop_front()


func show_lore(text: String) -> void:
	if quiet:
		return
	_lore.append({"text": text, "t": 0.0, "life": 6.5})


func set_boss(b: Node) -> void:
	_title_t = 0.0
	_boss = b
	_boss_label = b.label if b else ""
	_boss_ratio = 1.0


func clear_boss() -> void:
	_boss = null


func flash() -> void:
	_flicker = 0.25


func _process(delta: float) -> void:
	if _title_t > 0.0:
		_title_t -= delta
	for w in _whispers:
		w["t"] += delta
	_whispers = _whispers.filter(func(w): return w["t"] < w["life"])
	for l in _lore:
		l["t"] += delta
	_lore = _lore.filter(func(l): return l["t"] < l["life"])
	if _boss and is_instance_valid(_boss):
		_boss_ratio = _boss.hp_ratio()
		_boss_label = _boss.label
	_flicker = maxf(0.0, _flicker - delta)
	root.queue_redraw()


func _on_draw() -> void:
	var vp := Vector2(480, 270)
	_draw_health(vp)
	_draw_clarity(vp)
	_draw_madness(vp)
	if _boss and is_instance_valid(_boss) and _boss.active:
		_draw_boss_bar(vp)
	_draw_stage_title(vp)
	_draw_lore(vp)
	_draw_whispers(vp)


func _draw_health(_vp: Vector2) -> void:
	var hp := GameState.health
	var maxhp := GameState.max_health
	for i in maxhp:
		var t := _candle_full if i < hp else _candle_empty
		if t:
			root.draw_texture(t, Vector2(8 + i * 14, 5))
		else:
			root.draw_rect(Rect2(10 + i * 14, 8, 8, 16), Color(0.6, 0.5, 0.4))


func _draw_clarity(_vp: Vector2) -> void:
	var r := GameState.sanity_ratio()
	var x := 8.0
	var y := 32.0
	var w := 62.0
	root.draw_rect(Rect2(x - 1, y - 1, w + 2, 5), Color(0.05, 0.04, 0.04, 0.9))
	root.draw_rect(Rect2(x, y, w, 3), Color(0.14, 0.12, 0.13, 0.95))
	var col := Color(0.52, 0.78, 0.62)
	if r < 0.35:
		col = Color(0.78, 0.32, 0.28)
	elif r < 0.65:
		col = Color(0.78, 0.66, 0.36)
	root.draw_rect(Rect2(x, y, w * r, 3), col)
	# marca de umbral
	root.draw_rect(Rect2(x + w * 0.35, y - 1, 1, 5), Color(0.5, 0.16, 0.16, 0.7))
	PixelFont.draw(root, Vector2(8, 39), I18n.t("ui.clarity"), 1, Color(0.45, 0.55, 0.48), false)


func _draw_madness(vp: Vector2) -> void:
	var tier := GameState.tier()
	var x := vp.x - 44
	if _eye:
		var pulse := 1.0 + sin(Time.get_ticks_msec() * 0.004) * 0.05 * GameState.madness_ratio()
		root.draw_set_transform(Vector2(x + 9, 16), 0.0, Vector2(pulse, pulse))
		root.draw_texture(_eye, Vector2(-9, -9))
		root.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# pips
	for i in 7:
		var px := float(vp.x - 78 + i * 6)
		var on := i < tier
		root.draw_rect(Rect2(px, 30, 4, 4), Color(0.75, 0.45, 0.85) if on else Color(0.18, 0.15, 0.2))
	PixelFont.draw(root, Vector2(vp.x - 78, 38), "%s %d/7" % [I18n.t("ui.madness"), tier], 1,
			Color(0.62, 0.45, 0.68), false)


func _draw_boss_bar(vp: Vector2) -> void:
	var w := 190.0
	var x := (vp.x - w) * 0.5
	var y := vp.y - 24.0
	root.draw_rect(Rect2(x - 1, y - 1, w + 2, 7), Color(0.04, 0.03, 0.04, 0.92))
	root.draw_rect(Rect2(x, y, w, 5), Color(0.16, 0.10, 0.12, 0.95))
	var col := Color(0.62, 0.14, 0.16)
	if _boss_ratio < 0.3:
		col = Color(0.85, 0.32, 0.18)
	root.draw_rect(Rect2(x, y, w * _boss_ratio, 5), col)
	var shine := sin(Time.get_ticks_msec() * 0.006) * 0.12 + 0.88
	root.draw_rect(Rect2(x, y, w * _boss_ratio, 1), Color(0.9, 0.6, 0.55, shine * 0.5))
	PixelFont.draw_centered(root, vp.x * 0.5, y - 12, _boss_label, 1, Color(0.82, 0.72, 0.66), true)


func _draw_stage_title(vp: Vector2) -> void:
	if _title_t <= 0.0:
		return
	var a := clampf(_title_t, 0.0, 1.0)
	a = minf(a, clampf((5.4 - _title_t) / 0.9, 0.0, 1.0))
	var col := Color(0.86, 0.82, 0.70, a)
	PixelFont.draw_centered(root, vp.x * 0.5, 84, _stage_title, 2, col, true)
	PixelFont.draw_centered(root, vp.x * 0.5, 104, _subtitle, 1,
			Color(0.62, 0.66, 0.60, a), true)
	if _intro != "":
		var y := 128.0
		var ia := a * clampf((_title_t - 0.6) / 1.2, 0.0, 1.0)
		for line in _intro.split("\n"):
			PixelFont.draw_centered(root, vp.x * 0.5, y, line, 1, Color(0.72, 0.70, 0.60, ia))
			y += 10.0


func _draw_lore(vp: Vector2) -> void:
	if _lore.is_empty():
		return
	var l: Dictionary = _lore.back()
	var t: float = l["t"]
	var a := clampf(t / 0.5, 0.0, 1.0) * clampf((float(l["life"]) - t) / 0.9, 0.0, 1.0)
	var text: String = l["text"]
	if text == "":
		return
	var w := 268
	var lines := PixelFont._wrap(text, PixelFont.char_width(1), w)
	var panel_h: float = lines.size() * 10.0 + 26.0
	var pos := Vector2((vp.x - w) * 0.5, 176.0)
	root.draw_rect(Rect2(pos.x - 8, pos.y - 8, w + 16, panel_h), Color(0.03, 0.03, 0.04, 0.82 * a))
	root.draw_rect(Rect2(pos.x - 8, pos.y - 8, w + 16, 1), Color(0.45, 0.38, 0.26, 0.7 * a))
	PixelFont.draw(root, pos, text, 1, Color(0.86, 0.82, 0.70, a), false, w)
	PixelFont.draw(root, Vector2(pos.x, pos.y + lines.size() * 10.0 + 6.0), I18n.t("ui.fragment"), 1,
			Color(0.58, 0.52, 0.38, a * 0.85), false)


func _draw_whispers(vp: Vector2) -> void:
	var i := 0
	for w in _whispers:
		var t: float = w["t"]
		var life: float = w["life"]
		var a := clampf(t / 0.6, 0.0, 1.0) * clampf((life - t) / 1.2, 0.0, 1.0)
		var y := 62.0 + i * 10.0 + sin(t * 0.8) * 1.5
		PixelFont.draw_centered(root, vp.x * 0.5, y, w["text"], 1,
				Color(0.58, 0.74, 0.66, a * 0.7), false)
		i += 1
