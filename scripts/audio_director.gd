extends Node
## Director de audio: ambiente por etapa, capa de jefes y SFX.
## Los .wav son generados por tools/gen_audio.py.

const AMB_FILES := [
	"res://assets/audio/amb_1.wav", "res://assets/audio/amb_2.wav",
	"res://assets/audio/amb_3.wav", "res://assets/audio/amb_4.wav",
	"res://assets/audio/amb_5.wav", "res://assets/audio/amb_6.wav",
	"res://assets/audio/amb_7.wav",
]
const BOSS_FILE := "res://assets/audio/mus_boss.wav"
const SFX := {
	"swing": "res://assets/audio/sfx_swing.wav",
	"hit": "res://assets/audio/sfx_hit.wav",
	"hurt": "res://assets/audio/sfx_hurt.wav",
	"dash": "res://assets/audio/sfx_dash.wav",
	"voice": "res://assets/audio/sfx_voice.wav",
	"death": "res://assets/audio/sfx_death.wav",
	"checkpoint": "res://assets/audio/sfx_checkpoint.wav",
	"pickup": "res://assets/audio/sfx_pickup.wav",
	"whisper": "res://assets/audio/sfx_whisper.wav",
	"boss_roar": "res://assets/audio/sfx_boss_roar.wav",
	"land": "res://assets/audio/sfx_land.wav",
	"menu": "res://assets/audio/sfx_menu.wav",
}

var amb_player: AudioStreamPlayer
var boss_player: AudioStreamPlayer
var _sfx_players: Array[AudioStreamPlayer] = []
var _cache: Dictionary = {}
var _current_amb: int = -1
var _boss_on: bool = false

const SFX_VOICES := 8


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	amb_player = AudioStreamPlayer.new()
	amb_player.bus = "Master"
	amb_player.volume_db = -9.0
	add_child(amb_player)
	boss_player = AudioStreamPlayer.new()
	boss_player.bus = "Master"
	boss_player.volume_db = -13.0
	add_child(boss_player)
	for i in SFX_VOICES:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_sfx_players.append(p)


func _stream(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	if not ResourceLoader.exists(path):
		return null
	var s := load(path)
	_cache[path] = s
	return s


func _looped(s: AudioStream) -> AudioStream:
	if s is AudioStreamWAV:
		var w := s as AudioStreamWAV
		if w.loop_mode == AudioStreamWAV.LOOP_DISABLED:
			w.loop_mode = AudioStreamWAV.LOOP_FORWARD
			w.loop_begin = 0
			w.loop_end = int(w.get_length() * w.mix_rate)
	return s


func play_ambience(index: int) -> void:
	index = clampi(index, 0, AMB_FILES.size() - 1)
	if index == _current_amb and amb_player.playing:
		return
	_current_amb = index
	var s := _stream(AMB_FILES[index])
	if s == null:
		return
	amb_player.stream = _looped(s)
	amb_player.play()
	_fade(amb_player, -10.0, 0.6)


func stop_ambience(fade: float = 1.0) -> void:
	_fade_out(amb_player, fade)
	_current_amb = -1


func start_boss_music() -> void:
	if _boss_on:
		return
	_boss_on = true
	var s := _stream(BOSS_FILE)
	if s == null:
		return
	boss_player.stream = _looped(s)
	boss_player.play()
	_fade(boss_player, -6.0, 1.2)
	if amb_player.playing:
		_fade(amb_player, -22.0, 1.2)


func stop_boss_music() -> void:
	if not _boss_on:
		return
	_boss_on = false
	_fade_out(boss_player, 1.5)
	if amb_player.playing:
		_fade(amb_player, -9.0, 1.5)


func sfx(name: String, pitch_var: float = 0.08, volume_db: float = -4.0) -> void:
	var path: String = SFX.get(name, "")
	if path == "":
		return
	var s := _stream(path)
	if s == null:
		return
	for p in _sfx_players:
		if not p.playing:
			p.stream = s
			p.pitch_scale = 1.0 + randf_range(-pitch_var, pitch_var)
			p.volume_db = volume_db
			p.play()
			return
	# si están todos ocupados, reutiliza el primero
	_sfx_players[0].stream = s
	_sfx_players[0].play()


func _fade(p: AudioStreamPlayer, target_db: float, time: float) -> void:
	var tw := create_tween()
	tw.tween_property(p, "volume_db", target_db, time)


func _fade_out(p: AudioStreamPlayer, time: float) -> void:
	if not p.playing:
		return
	var tw := create_tween()
	tw.tween_property(p, "volume_db", -40.0, time)
	tw.tween_callback(p.stop)
