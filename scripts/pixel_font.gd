class_name PixelFont
extends RefCounted
## Tipografía de mapa de bits generada por tools/gen_ui.py.
## Se dibuja a mano con draw_texture_rect_region: cero dependencias del importador.

const ATLAS_PATH := "res://assets/ui/font.png"
const DATA_PATH := "res://assets/ui/font.json"

static var _atlas: Texture2D = null
static var _glyphs: Dictionary = {}
static var _loaded: bool = false
static var CELL := Vector2i(6, 10)


static func _init_font() -> void:
	if _loaded:
		return
	_loaded = true
	if ResourceLoader.exists(ATLAS_PATH):
		_atlas = load(ATLAS_PATH)
	var f := FileAccess.open(DATA_PATH, FileAccess.READ)
	if f:
		var data: Dictionary = JSON.parse_string(f.get_as_text())
		if data and data.has("glyphs"):
			_glyphs = data["glyphs"]
			if data.has("cell"):
				CELL = Vector2i(int(data["cell"][0]), int(data["cell"][1]))


static func char_width(size: int) -> int:
	_init_font()
	return (CELL.x - 1) * size


static func line_height(size: int) -> int:
	_init_font()
	return int(CELL.y * size * 0.92)


static func measure(text: String, size: int = 1) -> Vector2:
	var longest := 0
	var lines := text.split("\n")
	for l in lines:
		longest = maxi(longest, l.length())
	return Vector2(longest * char_width(size), maxi(1, lines.size()) * line_height(size))


static func draw(ci: CanvasItem, pos: Vector2, text: String, size: int = 1,
		color: Color = Color(0.84, 0.81, 0.72), shadow: bool = true,
		max_width: int = 0) -> void:
	_init_font()
	if _atlas == null:
		return
	var s := maxi(1, size)
	var cw := char_width(s)
	var lh := line_height(s)
	var lines := _wrap(text, cw, max_width)
	var y := pos.y
	for line in lines:
		var x := pos.x
		for ch in line:
			var g: Array = _glyphs.get(ch, _glyphs.get(ch.to_upper(), []))
			if g.is_empty():
				if ch == " ":
					x += cw
					continue
				g = _glyphs.get(ch.to_upper(), [])
				if g.is_empty():
					x += cw
					continue
			var src := Rect2(float(g[0]), float(g[1]), float(g[2]), float(g[3]))
			var dst := Rect2(x, y, float(g[2]) * s, float(g[3]) * s)
			if shadow:
				ci.draw_texture_rect_region(_atlas, Rect2(dst.position + Vector2(s, s), dst.size), src,
						Color(0, 0, 0, 0.75))
			ci.draw_texture_rect_region(_atlas, dst, src, color)
			x += cw
		y += lh


static func draw_centered(ci: CanvasItem, center_x: float, y: float, text: String,
		size: int = 1, color: Color = Color(0.84, 0.81, 0.72), shadow: bool = true) -> void:
	var w := measure(text, size).x
	draw(ci, Vector2(round(center_x - w * 0.5), y), text, size, color, shadow)


static func _wrap(text: String, cw: int, max_width: int) -> PackedStringArray:
	if max_width <= 0:
		return PackedStringArray(text.split("\n"))
	var max_chars := maxi(4, int(max_width / float(cw)))
	var out := PackedStringArray()
	for paragraph in text.split("\n"):
		var line := ""
		for word in paragraph.split(" "):
			var candidate := word if line == "" else line + " " + word
			if candidate.length() > max_chars and line != "":
				out.append(line)
				line = word
			else:
				line = candidate
		out.append(line)
	return out
