extends Node3D

const AvatarRigScript = preload("res://scripts/avatar_rig.gd")
const GodotIPCServerScript = preload("res://scripts/ipc_server.gd")

@onready var avatar_rig: Node = $AvatarHolder
@onready var ipc_server: Node = $IPCServer
@onready var camera: Camera3D = $Camera3D

func _ready():
	get_tree().get_root().transparent_bg = true
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
	
	ipc_server.avatar_rig = avatar_rig
	
	var default_path = "/home/victor/.gemini/antigravity/scratch/jarvis_assistant/ui/static/vrm_models/Vanessa_Flagship_Anime.vrm"
	var cmd_args = OS.get_cmdline_user_args()
	for arg in cmd_args:
		if arg.begins_with("--model="):
			default_path = arg.substr(8)
	
	if FileAccess.file_exists(default_path):
		avatar_rig.load_model(default_path)

func _input(event: InputEvent):
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			var viewport = get_viewport()
			var mouse_pos = event.position
			var vp_size = viewport.get_visible_rect().size
			var norm_y = mouse_pos.y / max(1.0, vp_size.y)
			if norm_y < 0.35:
				ipc_server.broadcast({"event": "head_pat"})
				ipc_server.broadcast({"event": "avatar_clicked", "part": "head", "x": mouse_pos.x, "y": mouse_pos.y})
			else:
				ipc_server.broadcast({"event": "avatar_clicked", "part": "body", "x": mouse_pos.x, "y": mouse_pos.y})
	elif event is InputEventMouseMotion:
		var vp_size = get_viewport().get_visible_rect().size
		var norm_x = (event.position.x / max(1.0, vp_size.x)) * 2.0 - 1.0
		var norm_y = (event.position.y / max(1.0, vp_size.y)) * 2.0 - 1.0
		avatar_rig.look_at_normalized(norm_x, norm_y)
