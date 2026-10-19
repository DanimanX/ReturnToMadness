extends Node
## Bot de verificación: recorre una etapa de verdad (salta huecos, pega, esquiva).
## No es IA de juego: es un test de que el nivel se puede terminar.

var level: Level
var player: Player
var stuck: float = 0.0
var jump_hold: float = 0.0
var attack_hold: float = 0.0
var max_x: float = 0.0
var _last_x: float = 0.0
var _jump_cd: float = 0.0


func setup(l: Level, p: Player) -> void:
	level = l
	player = p
	max_x = p.global_position.x


func _physics_process(delta: float) -> void:
	if level == null or player == null or not is_instance_valid(player):
		return
	if player.is_dead():
		Input.action_release("move_right")
		Input.action_release("jump")
		Input.action_release("attack")
		return

	_jump_cd = maxf(0.0, _jump_cd - delta)
	max_x = maxf(max_x, player.global_position.x)

	var pos := player.global_position
	var dir := 1.0
	if absf(pos.x - _last_x) < 0.6:
		stuck += delta
	else:
		stuck = 0.0
	_last_x = pos.x

	var feet_row := int((pos.y + 3.0) / level.TILE)
	var front_col := int((pos.x + 18.0) / level.TILE)
	# mira tres columnas: mejor saltar antes que caer
	# solo la columna siguiente: saltar antes hace que el salto quede corto
	var danger := _danger_ahead(front_col, feet_row)
	danger = danger or _wall_ahead(front_col, feet_row)

	# salto: hueco, muro o atasco
	if player.is_on_floor() and _jump_cd <= 0.0 and (danger or stuck > 0.35):
		Input.action_press("jump")
		jump_hold = 0.42
		_jump_cd = 0.45
		stuck = 0.0
	if jump_hold > 0.0:
		jump_hold -= delta
		if jump_hold <= 0.0:
			Input.action_release("jump")

	# combate: pega si hay algo cerca
	var target := _nearest_threat(pos)
	# se mueve hacia el objetivo; si no hay, avanza a la derecha
	if target != null and target.global_position.x < pos.x - 6.0:
		Input.action_release("move_right")
		Input.action_press("move_left")
	else:
		Input.action_release("move_left")
		Input.action_press("move_right")
	if target != null:
		var dx: float = target.global_position.x - pos.x
		var dy: float = target.global_position.y - pos.y
		if absf(dx) < 34.0 and absf(dy) < 40.0 and not danger:
			if attack_hold <= 0.0:
				Input.action_press("attack")
				attack_hold = 0.35
				_jump_cd = 0.0
	if attack_hold > 0.0:
		attack_hold -= delta
		if attack_hold <= 0.0:
			Input.action_release("attack")

	# atascado en una arena: grita y esquiva
	if stuck > 1.6:
		Input.action_press("voice")
		Input.action_press("dash")
		get_tree().create_timer(0.1).timeout.connect(func():
			Input.action_release("voice")
			Input.action_release("dash"))
		stuck = 0.0


func _danger_ahead(col: int, row: int) -> bool:
	"""Hueco, pinchos, agua o un escalón que no se sube andando."""
	var support := -99
	for dy in range(-2, 4):
		var c := level.cell(col, row + dy)
		if c == "^" or c == "~":
			return true
		if c == "#" and support == -99:
			support = row + dy
	if support == -99:
		return true                      # vacío: hay que saltar
	if support <= row - 1:
		return true                      # escalón hacia arriba
	if support - row >= 2:
		return true                      # borde de foso
	return false


func _wall_ahead(col: int, row: int) -> bool:
	return level.is_solid(col, row - 1) and level.is_solid(col, row - 2)


func _nearest_threat(pos: Vector2) -> Node2D:
	var best: Node2D = null
	var best_d := 70.0
	for e in get_tree().get_nodes_in_group("enemies"):
		if not is_instance_valid(e):
			continue
		if e.has_method("is_dead") and e.is_dead():
			continue
		var d: float = pos.distance_to(e.global_position)
		if d < best_d:
			best_d = d
			best = e
	return best
