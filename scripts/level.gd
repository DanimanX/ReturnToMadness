extends Node2D
class_name Level
## Construye una etapa desde un mapa ASCII (data/stages.gd).
## Autotile por vecinos, colisión fusionada en rectángulos, props y criaturas.

signal gate_reached
signal checkpoint_activated(pos: Vector2)
signal lore_collected(text: String)
signal boss_started(boss: Node)
signal boss_defeated

const TILE := 16
const ROWS := 17

const SOLID := "#"
const PLATFORM := "="
const SPIKE := "^"
const WATER := "~"

var stage: Dictionary = {}
var stage_index: int = 0

var grid: Array = []              # Array[PackedStringArray] filas de chars
var width_tiles: int = 0
var tilemap: TileMapLayer
var solid_body: StaticBody2D
var oneway_body: StaticBody2D
var hazards: Node2D
var props: Node2D
var entities: Node2D
var player: Player
var spawn_point := Vector2.ZERO
var gate_pos := Vector2.ZERO
var camera: Camera2D
var boss: Node = null
var active_checkpoint := Vector2.ZERO

var _enemies: Array = []
var _books: Array = []
var _gate_area: Area2D
var _gate_fired: bool = false
var _altars: Array = []
var _book_index: int = 0

const ENEMY_SCRIPTS := "res://scripts/enemy.gd"


func build(data: Dictionary, index: int) -> void:
	stage = data
	stage_index = index
	_parse_map()
	_build_background()
	_build_tiles()
	_build_collision()
	_build_entities()
	_build_camera()
	_update_progress()


func _update_progress() -> void:
	if player and is_instance_valid(player):
		var p := clampf(player.global_position.x / maxf(1.0, width_tiles * TILE - 240.0), 0.0, 1.0)
		GameState.set_stage_progress(p)


# ------------------------------------------------------------------ mapa
func _parse_map() -> void:
	grid.clear()
	width_tiles = 0
	var rows: Array = stage.get("map", [])
	for r in rows:
		width_tiles = maxi(width_tiles, String(r).length())
	for r in rows:
		var s := String(r)
		while s.length() < width_tiles:
			s += "."
		grid.append(s)
	while grid.size() < ROWS:
		grid.append(".".repeat(width_tiles))


func cell(x: int, y: int) -> String:
	if y < 0 or y >= grid.size() or x < 0 or x >= width_tiles:
		return "."
	return grid[y][x]


func is_solid(x: int, y: int) -> bool:
	var c := cell(x, y)
	return c == SOLID


# ------------------------------------------------------------------ fondo
func _build_background() -> void:
	var bg := ParallaxBackground.new()
	bg.name = "Parallax"
	add_child(bg)

	var far_path := "res://assets/bg/bg_%d_far.png" % (stage_index + 1)
	var near_path := "res://assets/bg/bg_%d_near.png" % (stage_index + 1)
	var layers := [
		[far_path, 0.22, -100],
		[near_path, 0.48, -50],
	]
	for spec in layers:
		if not ResourceLoader.exists(spec[0]):
			continue
		var layer := ParallaxLayer.new()
		layer.motion_scale = Vector2(spec[1], 0.08)
		layer.motion_mirroring = Vector2(1600, 0)
		bg.add_child(layer)
		var spr := Sprite2D.new()
		spr.texture = load(spec[0])
		spr.centered = false
		spr.position = Vector2(0, 0)
		spr.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		spr.z_index = spec[2]
		layer.add_child(spr)

	# niebla cercana que se mueve sola
	var fog_layer := ParallaxLayer.new()
	fog_layer.motion_scale = Vector2(0.7, 0.0)
	bg.add_child(fog_layer)
	var fog_rect := ColorRect.new()
	fog_rect.color = Color(0.10, 0.14, 0.14, 0.10)
	fog_rect.size = Vector2(width_tiles * TILE + 960, 270)
	fog_rect.position = Vector2(-240, 120)
	fog_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fog_layer.add_child(fog_rect)


# ------------------------------------------------------------------ tiles
func _build_tiles() -> void:
	tilemap = TileMapLayer.new()
	tilemap.name = "Tiles"
	tilemap.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	tilemap.z_index = -10
	add_child(tilemap)

	var mat: String = stage.get("material", "rock")
	var path := "res://assets/tiles/tiles_%s.png" % mat
	if not ResourceLoader.exists(path):
		path = "res://assets/tiles/tiles_rock.png"
	if not ResourceLoader.exists(path):
		return

	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE, TILE)
	var src := TileSetAtlasSource.new()
	src.texture = load(path)
	src.texture_region_size = Vector2i(TILE, TILE)
	for ty in 2:
		for tx in 8:
			src.create_tile(Vector2i(tx, ty))
	ts.add_source(src, 0)
	tilemap.tile_set = ts

	for y in grid.size():
		for x in width_tiles:
			var c := cell(x, y)
			var atlas := _tile_for(x, y, c)
			if atlas.x >= 0:
				tilemap.set_cell(Vector2i(x, y), 0, atlas, 0)


func _tile_for(x: int, y: int, c: String) -> Vector2i:
	if c == SOLID:
		var up := is_solid(x, y - 1)
		var dn := is_solid(x, y + 1)
		var lf := is_solid(x - 1, y)
		var rt := is_solid(x + 1, y)
		if not up and not lf:
			return Vector2i(2, 0)
		if not up and not rt:
			return Vector2i(3, 0)
		if not up:
			return Vector2i(1, 0)
		if not lf:
			return Vector2i(4, 0)
		if not rt:
			return Vector2i(5, 0)
		if not dn:
			return Vector2i(6, 0)
		# variante de ladrillo de vez en cuando
		if (x * 7 + y * 13) % 23 == 0:
			return Vector2i(4, 1)
		return Vector2i(0, 0)
	if c == PLATFORM:
		return Vector2i(0, 1)
	if c == SPIKE:
		return Vector2i(1, 1)
	if c == WATER:
		return Vector2i(0, 1) if cell(x, y - 1) != WATER else Vector2i(3, 1)
	return Vector2i(-1, -1)


# ------------------------------------------------------------------ colisión
func _build_collision() -> void:
	solid_body = StaticBody2D.new()
	solid_body.name = "Solid"
	solid_body.collision_layer = 1
	add_child(solid_body)

	oneway_body = StaticBody2D.new()
	oneway_body.name = "OneWay"
	oneway_body.collision_layer = 1
	add_child(oneway_body)

	var visited := {}
	var plate_w := width_tiles * TILE
	var plate_h := grid.size() * TILE

	for y in grid.size():
		for x in width_tiles:
			if cell(x, y) != SOLID or visited.has(Vector2i(x, y)):
				continue
			# ancho de la corrida
			var w := 0
			while x + w < width_tiles and cell(x + w, y) == SOLID and not visited.has(Vector2i(x + w, y)):
				w += 1
			# alto de la corrida (misma ventana horizontal)
			var h := 1
			while y + h < grid.size():
				var ok := true
				for k in w:
					if cell(x + k, y + h) != SOLID or visited.has(Vector2i(x + k, y + h)):
						ok = false
						break
				if not ok:
					break
				h += 1
			for yy in h:
				for xx in w:
					visited[Vector2i(x + xx, y + yy)] = true
			_add_rect(solid_body, x, y, w, h)

	# plataformas de un solo sentido
	var pvisited := {}
	for y in grid.size():
		for x in width_tiles:
			if cell(x, y) != PLATFORM or pvisited.has(Vector2i(x, y)):
				continue
			var w := 0
			while x + w < width_tiles and cell(x + w, y) == PLATFORM and not pvisited.has(Vector2i(x + w, y)):
				w += 1
			for k in w:
				pvisited[Vector2i(x + k, y)] = true
			var shape := CollisionShape2D.new()
			var rect := RectangleShape2D.new()
			rect.size = Vector2(w * TILE, 6)
			shape.shape = rect
			shape.position = Vector2(x * TILE + w * TILE * 0.5, y * TILE + 3)
			shape.one_way_collision = true
			shape.one_way_collision_margin = 4.0
			oneway_body.add_child(shape)

	# límites invisibles: el jugador no sale del mundo
	for spec in [[-8, 0, 8, grid.size() * TILE], [width_tiles * TILE, 0, 8, grid.size() * TILE]]:
		var lim := CollisionShape2D.new()
		var lr := RectangleShape2D.new()
		lr.size = Vector2(spec[2], spec[3])
		lim.shape = lr
		lim.position = Vector2(spec[0] + spec[2] * 0.5, spec[3] * 0.5)
		solid_body.add_child(lim)

	# pinchos y agua
	hazards = Node2D.new()
	hazards.name = "Hazards"
	add_child(hazards)
	_build_hazard_rows(SPIKE, 10.0)
	_build_hazard_rows(WATER, 18.0)

	if plate_w > 0:
		pass


func _add_rect(body: StaticBody2D, x: int, y: int, w: int, h: int) -> void:
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(w * TILE, h * TILE)
	shape.shape = rect
	shape.position = Vector2(x * TILE + w * TILE * 0.5, y * TILE + h * TILE * 0.5)
	body.add_child(shape)


func _build_hazard_rows(ch: String, damage: float) -> void:
	var visited := {}
	for y in grid.size():
		var x := 0
		while x < width_tiles:
			if cell(x, y) != ch or visited.has(Vector2i(x, y)):
				x += 1
				continue
			var w := 0
			while x + w < width_tiles and cell(x + w, y) == ch:
				w += 1
			for k in w:
				visited[Vector2i(x + k, y)] = true
			var area := Area2D.new()
			area.collision_layer = 8   # capa 4: peligro
			area.collision_mask = 2    # detecta al jugador
			area.monitoring = true
			var shape := CollisionShape2D.new()
			var rect := RectangleShape2D.new()
			rect.size = Vector2(w * TILE, TILE * 0.75)
			shape.shape = rect
			shape.position = Vector2(x * TILE + w * TILE * 0.5, y * TILE + TILE * 0.55)
			area.add_child(shape)
			area.set_meta("damage", damage)
			area.set_meta("hazard", ch)
			hazards.add_child(area)
			x += w


# ------------------------------------------------------------------ entidades
func _build_entities() -> void:
	props = Node2D.new()
	props.name = "Props"
	props.y_sort_enabled = true
	add_child(props)

	entities = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	add_child(entities)

	var gate_placed := false
	for y in grid.size():
		for x in width_tiles:
			var c := cell(x, y)
			var pos := Vector2(x * TILE + TILE * 0.5, y * TILE + TILE)
			match c:
				"P":
					spawn_point = pos
				"A":
					_altars.append(_spawn_altar(pos))
				"X":
					_spawn_gate(Vector2(x * TILE, y * TILE - 48))
					gate_placed = true
				"1":
					_spawn_enemy("ahogado", pos)
				"2":
					_spawn_enemy("cultista", pos)
				"3":
					_spawn_enemy("polipo", pos + Vector2(0, -24))
				"4":
					_spawn_enemy("bestia", pos)
				"5":
					_spawn_enemy("migo", pos + Vector2(0, -20))
				"T":
					_spawn_tentacle(pos)
				"B":
					_spawn_boss(pos)
				"b":
					_spawn_book(pos + Vector2(0, -10))
				"t":
					_spawn_torch(pos + Vector2(0, -8))
				"s":
					_spawn_statue(pos)
				":":
					_spawn_chain(pos)
	if not gate_placed:
		gate_pos = Vector2(width_tiles * TILE - 64, 0)
	if spawn_point == Vector2.ZERO:
		spawn_point = Vector2(48, 200)
	if _altars.is_empty():
		active_checkpoint = spawn_point


func _sprite(path: String, frames: int, fps: float) -> AnimatedSprite2D:
	var sf := SpriteFrames.new()
	var base := path.get_basename()
	for i in frames:
		var p := "%s_%d.png" % [base, i]
		if ResourceLoader.exists(p):
			sf.add_frame("default", load(p))
		elif ResourceLoader.exists(base + ".png"):
			sf.add_frame("default", load(base + ".png"))
	sf.set_animation_speed("default", fps)
	sf.set_animation_loop("default", true)
	var a := AnimatedSprite2D.new()
	a.sprite_frames = sf
	a.animation = "default"
	a.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	a.play()
	return a


func _spawn_altar(pos: Vector2) -> Node2D:
	var n := Node2D.new()
	n.position = pos
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_altar.png")
	s.offset = Vector2(0, -44)
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	n.add_child(s)
	var area := Area2D.new()
	area.collision_layer = 16
	area.collision_mask = 2
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(44, 56)
	shape.shape = rect
	shape.position = Vector2(0, -24)
	area.add_child(shape)
	area.set_meta("altar", true)
	area.set_meta("pos", pos)
	n.add_child(area)
	n.set_meta("altar", true)
	n.set_meta("lit", false)
	add_glow(n, Vector2(0, -32), 1.1, Color(1.0, 0.72, 0.40), 0.30, -1)
	props.add_child(n)
	return n


func _spawn_gate(pos: Vector2) -> void:
	gate_pos = pos
	var n := Node2D.new()
	n.position = pos + Vector2(20, 64)
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_gate.png")
	s.offset = Vector2(0, -64)
	s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	n.add_child(s)
	var area := Area2D.new()
	area.collision_layer = 16
	area.collision_mask = 2
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(36, 64)
	shape.shape = rect
	shape.position = Vector2(0, -32)
	area.add_child(shape)
	area.set_meta("gate", true)
	n.add_child(area)
	n.set_meta("gate", true)
	add_glow(n, Vector2(0, -34), 1.6, Color(0.55, 0.85, 0.72), 0.30, -1)
	props.add_child(n)
	_gate_area = area


func _spawn_book(pos: Vector2) -> void:
	var n := Node2D.new()
	n.position = pos
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_book.png")
	s.offset = Vector2(0, -8)
	n.add_child(s)
	add_glow(n, Vector2(0, -8), 0.55, Color(1.0, 0.85, 0.55), 0.35, -1)
	var area := Area2D.new()
	area.collision_layer = 16
	area.collision_mask = 2
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(20, 20)
	shape.shape = rect
	area.add_child(shape)
	n.add_child(area)
	n.set_meta("book", true)
	# los fragmentos se reparten en orden: frag.0, frag.1, frag.2
	var key := String(stage.get("key", ""))
	var text := I18n.t("stage.%s.frag.%d" % [key, _book_index % 3])
	_book_index += 1
	n.set_meta("text", text)
	props.add_child(n)
	_books.append(n)


func _spawn_torch(pos: Vector2) -> void:
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_torch.png")
	s.position = pos
	s.offset = Vector2(0, -16)
	props.add_child(s)
	add_glow(props, pos + Vector2(0, -22), 0.95, Color(1.0, 0.68, 0.34), 0.42, -1)


func _spawn_statue(pos: Vector2) -> void:
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_statue.png")
	s.position = pos
	s.offset = Vector2(0, -52)
	props.add_child(s)


func _spawn_chain(pos: Vector2) -> void:
	var s := Sprite2D.new()
	s.texture = load("res://assets/sprites/prop_chain.png")
	s.position = pos + Vector2(0, -32)
	props.add_child(s)


func _spawn_tentacle(pos: Vector2) -> void:
	var t: TentacleHazard = load("res://scripts/tentacle.gd").new()
	t.position = pos
	t.set_meta("damage", 16.0)
	var spr := _sprite("res://assets/sprites/prop_tentacle_0.png", 3, 5.0)
	spr.name = "Sprite"
	spr.offset = Vector2(0, -40)
	t.add_child(spr)
	t.offset_phase = fmod(pos.x * 0.013, 1.6)
	props.add_child(t)
	t.setup()
	add_glow(t, Vector2(0, -22), 0.55, Color(0.85, 0.35, 0.55), 0.22, -1)


func _spawn_enemy(kind: String, pos: Vector2) -> void:
	var e: Enemy = load(ENEMY_SCRIPTS).new()
	e.kind = kind
	e.position = pos
	e.level = self
	entities.add_child(e)
	_enemies.append(e)


func _spawn_boss(pos: Vector2) -> void:
	var b: Boss = load("res://scripts/boss.gd").new()
	b.boss_index = stage_index
	b.position = pos
	b.level = self
	entities.add_child(b)
	boss = b
	b.defeated.connect(_on_boss_defeated)
	b.activated.connect(_on_boss_activated)


func _on_boss_activated() -> void:
	boss_started.emit(boss)


func _on_boss_defeated() -> void:
	boss_defeated.emit()


# ------------------------------------------------------------------ cámara
func _build_camera() -> void:
	camera = Camera2D.new()
	camera.name = "Camera"
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 7.0
	camera.limit_left = 0
	camera.limit_right = width_tiles * TILE
	camera.limit_top = 0
	camera.limit_bottom = grid.size() * TILE
	camera.drag_vertical_enabled = false
	add_child(camera)
	camera.make_current()


func attach_player(p: Player) -> void:
	player = p
	# la cámara cuelga del jugador: sigue su posición con suavizado y topes
	camera.reparent(p, false)
	camera.position = Vector2(0, -44)
	camera.limit_left = 0
	camera.limit_right = width_tiles * TILE
	camera.limit_top = 0
	camera.limit_bottom = grid.size() * TILE
	camera.reset_smoothing()


func add_glow(parent: Node, pos: Vector2, scale_v: float, color: Color, alpha: float = 0.7, z: int = -1) -> Sprite2D:
	var g := Sprite2D.new()
	g.texture = load("res://assets/sprites/fx_glow_warm.png")
	g.position = pos
	g.modulate = Color(color.r, color.g, color.b, alpha)
	g.scale = Vector2(scale_v, scale_v)
	g.z_index = z
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	g.material = mat
	parent.add_child(g)
	return g


# ------------------------------------------------------------------ por frame
func _process(delta: float) -> void:
	if player and is_instance_valid(player):
		# progreso horizontal -> locura
		var progress := clampf(player.global_position.x / maxf(1.0, width_tiles * TILE - 240.0), 0.0, 1.0)
		GameState.set_stage_progress(progress)
		_check_areas()


func _check_areas() -> void:
	if player == null or not is_instance_valid(player) or player.is_dead():
		return
	var ppos := player.global_position
	for a in _altars:
		if not is_instance_valid(a) or a.get_meta("lit", false):
			continue
		if ppos.distance_to(a.position + Vector2(0, -20)) < 34.0:
			a.set_meta("lit", true)
			active_checkpoint = a.position
			GameState.add_clarity(45.0)
			GameState.save_game()
			AudioDirector.sfx("checkpoint", 0.02, -3.0)
			checkpoint_activated.emit(a.position)
			_flash_altar(a)
	# la puerta solo cede cuando el guardián ya no respira;
	# tocar antes no la consume (antes era un fallo que bloqueaba la etapa)
	if _gate_area and not _gate_fired and ppos.distance_to(_gate_area.global_position) < 44.0:
		var guardian_alive: bool = boss != null and is_instance_valid(boss) and not boss.is_dead()
		if not guardian_alive:
			_gate_fired = true
			gate_reached.emit()
	for b in _books.duplicate():
		if not is_instance_valid(b):
			_books.erase(b)
			continue
		if b.get_meta("taken", false):
			continue
		if ppos.distance_to(b.position + Vector2(0, -10)) < 26.0:
			b.set_meta("taken", true)
			var text: String = String(b.get_meta("text", ""))
			GameState.add_lore(text)
			AudioDirector.sfx("pickup", 0.02, -5.0)
			lore_collected.emit(text)
			_books.erase(b)
			var tw := create_tween()
			tw.tween_property(b, "modulate:a", 0.0, 0.4)
			tw.tween_callback(b.queue_free)


func _flash_altar(a: Node2D) -> void:
	var g := add_glow(props, a.position + Vector2(0, -30), 2.4, Color(1.0, 0.78, 0.45), 0.85, -1)
	var tw := create_tween()
	tw.tween_property(g, "modulate:a", 0.25, 1.6)


func enemies() -> Array:
	return _enemies


func alive_enemies() -> int:
	var n := 0
	for e: Node in _enemies:
		if is_instance_valid(e) and e.has_method("is_dead") and not e.is_dead():
			n += 1
	return n
