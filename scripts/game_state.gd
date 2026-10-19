extends Node
## Estado global de la partida: locura persistente, cordura, progreso.
## La locura NUNCA baja. Es el precio de avanzar.

signal madness_changed(value: float)
signal clarity_changed(value: float)
signal health_changed(value: int)

const SAVE_PATH := "user://regreso_locura.save"
const MAX_MADNESS := 7.0
const MADNESS_PER_STAGE := 1.0

var stage_index: int = 0          # 0..6
var madness: float = 0.0          # 0..7, permanente
var clarity: float = 100.0        # 0..100, por etapa
var health: int = 3
var max_health: int = 3
var deaths: int = 0
var lore_found: PackedStringArray = PackedStringArray()
var stage_deaths: int = 0
var echo_loop: int = 0            # vueltas completadas (modo REGRESO)
var run_time: float = 0.0

var _stage_kill_madness: float = 0.0
var _stage_progress: float = 0.0


func reset_run() -> void:
	stage_index = 0
	madness = 0.0
	deaths = 0
	stage_deaths = 0
	lore_found = PackedStringArray()
	echo_loop = 0
	run_time = 0.0
	start_stage(0)


func start_stage(index: int) -> void:
	stage_index = clampi(index, 0, 6)
	# al entrar a una etapa ya se llega con la locura de las anteriores
	madness = maxf(madness, float(stage_index) * 0.85)
	clarity = 100.0
	health = max_health
	_stage_kill_madness = 0.0
	_stage_progress = 0.0
	stage_deaths = 0
	madness_changed.emit(madness)
	clarity_changed.emit(clarity)
	health_changed.emit(health)


func tier() -> int:
	return int(floor(clampf(madness, 0.0, MAX_MADNESS)))


func madness_ratio() -> float:
	return clampf(madness / MAX_MADNESS, 0.0, 1.0)


func sanity_ratio() -> float:
	return clampf(clarity / 100.0, 0.0, 1.0)


## Se llama con el avance dentro de la etapa (0..1).
func set_stage_progress(p: float) -> void:
	_stage_progress = clampf(p, 0.0, 1.0)
	_recompute()


func add_madness(amount: float) -> void:
	madness = clampf(madness + amount, 0.0, MAX_MADNESS)
	madness_changed.emit(madness)


func add_kill_madness(amount: float) -> void:
	# matar también revela; con tope por etapa para no romper el ritmo
	var room := maxf(0.0, 0.55 - _stage_kill_madness)
	var add := minf(amount, room)
	_stage_kill_madness += add
	add_madness(add)


func _recompute() -> void:
	var target := float(stage_index) + _stage_progress * 0.75 + _stage_kill_madness
	if target > madness:
		madness = minf(target, MAX_MADNESS)
		madness_changed.emit(madness)


func add_clarity(amount: float) -> void:
	clarity = clampf(clarity + amount, 0.0, 100.0)
	clarity_changed.emit(clarity)


func drain_clarity(amount: float) -> void:
	clarity = clampf(clarity - amount, 0.0, 100.0)
	clarity_changed.emit(clarity)


func clarity_empty() -> bool:
	return clarity <= 0.0


func set_health(v: int) -> void:
	health = clampi(v, 0, max_health)
	health_changed.emit(health)


func damage_multiplier() -> float:
	return 1.0 + 0.13 * madness


func taken_multiplier() -> float:
	return 1.0 + 0.09 * madness


func register_death() -> void:
	deaths += 1
	stage_deaths += 1
	add_madness(0.12)


func complete_stage() -> void:
	add_madness(MADNESS_PER_STAGE)
	_stage_kill_madness = 0.0
	_stage_progress = 0.0
	madness = clampf(madness, 0.0, MAX_MADNESS)
	madness_changed.emit(madness)


func add_lore(text: String) -> void:
	if not lore_found.has(text):
		lore_found.append(text)
		add_clarity(16.0)


# ------------------------------------------------------------------ guardado
func save_game() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("run", "stage_index", stage_index)
	cfg.set_value("run", "madness", madness)
	cfg.set_value("run", "deaths", deaths)
	cfg.set_value("run", "echo_loop", echo_loop)
	cfg.set_value("run", "run_time", run_time)
	cfg.set_value("run", "lore", lore_found)
	cfg.save(SAVE_PATH)


func wipe_save() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func load_game() -> bool:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) != OK:
		return false
	stage_index = int(cfg.get_value("run", "stage_index", 0))
	madness = float(cfg.get_value("run", "madness", 0.0))
	deaths = int(cfg.get_value("run", "deaths", 0))
	echo_loop = int(cfg.get_value("run", "echo_loop", 0))
	run_time = float(cfg.get_value("run", "run_time", 0.0))
	lore_found = PackedStringArray(cfg.get_value("run", "lore", []))
	start_stage(stage_index)
	return true


func _process(delta: float) -> void:
	run_time += delta
