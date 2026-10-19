extends CanvasLayer
class_name MadnessFX
## Director de la locura visible: post-proceso, alucinaciones, susurros y ojos.

var rect: ColorRect
var mat: ShaderMaterial
var world: Node2D
var hud: HUD

var _hurt: float = 0.0
var _voice: float = 0.0
var _spawn_t: float = 0.0
var _whisper_t: float = 0.0
var _eye_t: float = 0.0
var _rng := RandomNumberGenerator.new()

const WHISPER_COUNT := 12

var _eyes: Array = []


func _ready() -> void:
	layer = 10
	_rng.randomize()
	rect = ColorRect.new()
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rect.color = Color.WHITE
	var sh: Shader = load("res://shaders/madness.gdshader")
	if sh:
		mat = ShaderMaterial.new()
		mat.shader = sh
		rect.material = mat
	add_child(rect)


func trigger_hurt() -> void:
	_hurt = 1.0


func trigger_voice() -> void:
	_voice = 1.0


func _process(delta: float) -> void:
	_hurt = maxf(0.0, _hurt - delta * 2.4)
	_voice = maxf(0.0, _voice - delta * 2.0)
	if mat:
		mat.set_shader_parameter("madness", GameState.madness_ratio())
		mat.set_shader_parameter("sanity", GameState.sanity_ratio())
		mat.set_shader_parameter("hurt_flash", _hurt)
		mat.set_shader_parameter("voice_flash", _voice)
	var tier := GameState.tier()
	if tier >= 2:
		_spawn_t -= delta
		if _spawn_t <= 0.0:
			_spawn_t = maxf(1.6, 7.0 - tier * 0.8) * _rng.randf_range(0.6, 1.4)
			_hallucinate()
	if tier >= 1:
		_whisper_t -= delta
		if _whisper_t <= 0.0:
			_whisper_t = maxf(5.0, 26.0 - tier * 3.0) * _rng.randf_range(0.7, 1.5)
			if hud:
				hud.whisper(I18n.t("whisper.%d" % (_rng.randi() % WHISPER_COUNT)))
	if tier >= 4 and not _eyes.is_empty():
		for e in _eyes:
			e["t"] += delta
		_eyes = _eyes.filter(func(e): return e["t"] < e["life"])


func _hallucinate() -> void:
	if world == null:
		return
	var tex_path := "res://assets/sprites/en_espectro.png"
	if not ResourceLoader.exists(tex_path):
		return
	var tex: Texture2D = load(tex_path)
	var cam := get_viewport().get_camera_2d()
	var center := cam.get_screen_center_position() if cam else Vector2.ZERO
	var width := get_viewport().get_visible_rect().size.x
	var side := -1.0 if _rng.randf() < 0.5 else 1.0
	var spr := Sprite2D.new()
	spr.texture = tex
	spr.centered = false
	spr.offset = Vector2(-24, -46)
	spr.position = Vector2(center.x + side * (width * 0.5 + 40.0),
			center.y + _rng.randf_range(-30.0, 70.0))
	spr.scale.x = -side
	spr.modulate = Color(0.35, 0.45, 0.5, 0.0)
	spr.z_index = -5
	world.add_child(spr)
	var dur := _rng.randf_range(2.2, 3.6)
	var tw := spr.create_tween()
	tw.set_parallel(true)
	tw.tween_property(spr, "modulate:a", 0.42, 0.5)
	tw.tween_property(spr, "position:x", spr.position.x - side * 130.0, dur)
	tw.chain().tween_property(spr, "modulate:a", 0.0, 1.0)
	tw.chain().tween_callback(spr.queue_free)
	if _rng.randf() < 0.5:
		AudioDirector.sfx("whisper", 0.1, -16.0)
