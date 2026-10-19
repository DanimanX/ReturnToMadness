extends Node
## Compatibilidad de mandos 8BitDo (Ultimate 2C / edición Wukong).
##
## SDL reconoce la mayoría de mandos y Godot normaliza sus índices, pero una
## edición especial puede llegar con un PID que no está en gamecontrollerdb.
## En ese caso SDL abre el mando como joystick "crudo": los ejes y botones
## siguen llegando, pero los índices no son los que espera InputMap. Este nodo
## detecta esos mandos y les aplica el mismo mapeo que usa la base de datos de
## SDL para el Ultimate 2C, sin depender de una versión concreta de Godot.

const ULTIMATE_2C_RAW := "a:b0,b:b1,x:b3,y:b4,leftshoulder:b6,rightshoulder:b7,back:b10,start:b11,guide:b12,leftstick:b13,rightstick:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,dpup:h0.1,dpdown:h0.4,dpleft:h0.8,dpright:h0.2"

# PIDs de la familia Ultimate 2C en Bluetooth / 2.4G (vendor 0x2DC8).
const ULTIMATE_2C_PIDS := [0x301B, 0x301C, 0x301D, 0x301E, 0x301F, 0x3020]

var _fixed: Dictionary = {}
var _reported: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Input.joy_connection_changed.connect(_on_joy_connection_changed)
	_scan()


func _scan() -> void:
	for device in Input.get_connected_joypads():
		_check(device)


func _on_joy_connection_changed(device: int, connected: bool) -> void:
	if connected:
		_check(device)
	else:
		_fixed.erase(device)
		_reported.erase(device)


func _check(device: int) -> void:
	var name := Input.get_joy_name(device)
	var guid := Input.get_joy_guid(device)
	if guid.is_empty():
		return

	var lower := name.to_lower()
	if not _reported.has(device) or _reported[device] != name:
		_reported[device] = name
		print("[input] mando %d: %s (%s, reconocido=%s)" % [
			device, name, guid, "sí" if Input.is_joy_known(device) else "no"])

	# Si SDL ya lo reconoce, sus eventos vienen normalizados: no tocamos nada.
	if Input.is_joy_known(device):
		return
	if _fixed.has(device):
		return

	var info := Input.get_joy_info(device)
	var pid := _parse_id(str(info.get("product_id", "0")))
	var is_8bitdo := lower.contains("8bitdo") or lower.contains("wukong") \
			or lower.contains("ultimate 2c") or pid in ULTIMATE_2C_PIDS
	if not is_8bitdo:
		return

	# El nombre no puede llevar comas (separan campos del mapeo).
	var mapping := "%s,%s,%s" % [guid, name.replace(",", " "), ULTIMATE_2C_RAW]
	Input.add_joy_mapping(mapping, true)
	_fixed[device] = true
	print("[input] mapeo de respaldo aplicado a %s" % name)


## Los IDs llegan como texto; según el driver pueden ser decimales o "0x....".
static func _parse_id(raw: String) -> int:
	if raw.begins_with("0x") or raw.begins_with("0X"):
		return raw.substr(2).hex_to_int()
	return raw.to_int()
