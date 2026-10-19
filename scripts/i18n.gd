extends Node
## Idiomas: español, inglés, francés, portugués, italiano.
## Los textos viven en assets/lang/*.json (generados por tools/gen_lang.py).
## La elección se guarda en user://settings.cfg y sobrevive al cierre.

signal language_changed(code: String)

const LANGS := ["es", "en", "fr", "pt", "it"]
const NATIVE := {
	"es": "ESPAÑOL", "en": "ENGLISH", "fr": "FRANÇAIS",
	"pt": "PORTUGUÊS", "it": "ITALIANO",
}
const DIR := "res://assets/lang/"
const SETTINGS := "user://settings.cfg"

var code: String = "es"
var _tables: Dictionary = {}
var _names: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_load_all()
	code = _saved_language()
	if not _tables.has(code):
		code = "es"


func _load_all() -> void:
	for lang in LANGS:
		var path := "%s%s.json" % [DIR, lang]
		var data: Variant = _read_json(path)
		if typeof(data) != TYPE_DICTIONARY:
			push_warning("I18n: no se pudo leer %s" % path)
			continue
		_tables[lang] = data.get("strings", {})
		_names[lang] = String(data.get("_name", NATIVE.get(lang, lang)))


## En el editor el .json es un archivo; exportado puede llegar como recurso JSON.
func _read_json(path: String) -> Variant:
	if FileAccess.file_exists(path):
		var f := FileAccess.open(path, FileAccess.READ)
		if f:
			var parsed: Variant = JSON.parse_string(f.get_as_text())
			if parsed != null:
				return parsed
	if ResourceLoader.exists(path):
		var res := ResourceLoader.load(path)
		if res is JSON:
			return (res as JSON).data
	return null


func _saved_language() -> String:
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS) == OK:
		var saved := String(cfg.get_value("ui", "language", "es"))
		if LANGS.has(saved):
			return saved
	return _system_language()


func _system_language() -> String:
	# si el sistema habla uno de los cinco, se respeta en el primer arranque
	var sys := OS.get_locale_language().to_lower()
	if LANGS.has(sys):
		return sys
	return "es"


func native_name(lang: String = "") -> String:
	var l := lang if lang != "" else code
	return _names.get(l, NATIVE.get(l, l.to_upper()))


func next(delta: int) -> String:
	var i := LANGS.find(code)
	if i < 0:
		i = 0
	i = posmod(i + delta, LANGS.size())
	set_language(LANGS[i])
	return code


func set_language(new_code: String, save: bool = true) -> void:
	if not _tables.has(new_code):
		return
	if new_code == code:
		return
	code = new_code
	if save:
		var cfg := ConfigFile.new()
		cfg.load(SETTINGS)
		cfg.set_value("ui", "language", code)
		cfg.save(SETTINGS)
	language_changed.emit(code)


func has_key(key: String) -> bool:
	var table: Dictionary = _tables.get(code, {})
	return table.has(key)


## Traducción con respaldo en español y, si falta, la propia clave.
func t(key: String, args: Array = []) -> String:
	var table: Dictionary = _tables.get(code, {})
	var text: String = String(table.get(key, ""))
	if text == "":
		var fallback: Dictionary = _tables.get("es", {})
		text = String(fallback.get(key, key))
	if not args.is_empty():
		return text % args
	return text


## Varias cadenas numeradas: speak("whisper", 0, 12) -> ["...", ...]
func list(prefix: String, count: int) -> PackedStringArray:
	var out := PackedStringArray()
	for i in count:
		out.append(t("%s.%d" % [prefix, i]))
	return out


func available() -> Array:
	var out := []
	for l in LANGS:
		if _tables.has(l):
			out.append({"code": l, "name": native_name(l)})
	return out
