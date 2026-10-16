extends Node3D
class_name AvatarRig

signal model_loaded_signal(model_name: String)
signal gesture_finished_signal(gesture_name: String)

var current_model_node: Node3D = null
var skeleton: Skeleton3D = null
var face_mesh: MeshInstance3D = null
var bone_map: Dictionary = {}
var initial_bone_rotations: Dictionary = {}

var is_walking: bool = false
var walk_speed: float = 1.0
var walk_direction: int = 1
var walk_phase: float = 0.0

var idle_timer: float = 0.0
var blink_timer: float = 0.0
var next_blink_interval: float = 3.5
var is_blinking: bool = false
var blink_progress: float = 0.0

var is_speaking: bool = false
var speech_timer: float = 0.0

var active_gesture: String = ""
var gesture_timer: float = 0.0
var gesture_duration: float = 2.0

var current_emotions: Dictionary = {}
var target_emotions: Dictionary = {}

var target_look: Vector2 = Vector2.ZERO
var current_look: Vector2 = Vector2.ZERO

var secondary_bones: Array = []
var secondary_velocities: Dictionary = {}
var secondary_offsets: Dictionary = {}

var bone_alias_table = {
	"hips": ["hips", "j_bip_c_hips", "hip", "pelvis", "センター", "下半身"],
	"spine": ["spine", "j_bip_c_spine", "spine1", "上半身"],
	"chest": ["chest", "j_bip_c_chest", "upperchest", "j_bip_c_upperchest", "spine2", "上半身2"],
	"neck": ["neck", "j_bip_c_neck", "首"],
	"head": ["head", "j_bip_c_head", "頭"],
	"left_upper_leg": ["leftupperleg", "j_bip_l_upperleg", "thigh_l", "left_thigh", "左足"],
	"left_lower_leg": ["leftlowerleg", "j_bip_l_lowerleg", "calf_l", "left_knee", "左ひざ"],
	"left_foot": ["leftfoot", "j_bip_l_foot", "foot_l", "左足首"],
	"right_upper_leg": ["rightupperleg", "j_bip_r_upperleg", "thigh_r", "right_thigh", "右足"],
	"right_lower_leg": ["rightlowerleg", "j_bip_r_lowerleg", "calf_r", "right_knee", "右ひざ"],
	"right_foot": ["rightfoot", "j_bip_r_foot", "foot_r", "右足首"],
	"left_upper_arm": ["leftupperarm", "j_bip_l_upperarm", "upperarm_l", "left_arm", "左腕"],
	"left_lower_arm": ["leftlowerarm", "j_bip_l_lowerarm", "forearm_l", "left_elbow", "左ひじ"],
	"left_hand": ["lefthand", "j_bip_l_hand", "hand_l", "左手首"],
	"right_upper_arm": ["rightupperarm", "j_bip_r_upperarm", "upperarm_r", "right_arm", "右腕"],
	"right_lower_arm": ["rightlowerarm", "j_bip_r_lowerarm", "forearm_r", "right_elbow", "右ひじ"],
	"right_hand": ["righthand", "j_bip_r_hand", "hand_r", "右手首"]
}

func _ready():
	randomize()
	next_blink_interval = randf_range(2.5, 5.0)

func load_model(path: String) -> bool:
	if not FileAccess.file_exists(path):
		return false
	
	var gltf = GLTFDocument.new()
	var state = GLTFState.new()
	var err = gltf.append_from_file(path, state)
	if err != OK:
		return false
	
	var new_scene = gltf.generate_scene(state)
	if new_scene == null:
		return false
	
	if current_model_node != null:
		remove_child(current_model_node)
		current_model_node.queue_free()
		current_model_node = null
	
	skeleton = null
	face_mesh = null
	bone_map.clear()
	initial_bone_rotations.clear()
	secondary_bones.clear()
	secondary_velocities.clear()
	secondary_offsets.clear()
	
	current_model_node = new_scene
	add_child(current_model_node)
	current_model_node.rotation.y = PI
	
	_discover_components(current_model_node)
	_bind_bones()
	_bind_secondary_bones()
	
	model_loaded_signal.emit(path.get_file().get_basename())
	return true

func _discover_components(node: Node):
	if node is Skeleton3D and skeleton == null:
		skeleton = node
	if node is MeshInstance3D:
		if node.mesh != null and node.mesh.get_blend_shape_count() > 0:
			if face_mesh == null or node.name.to_lower().contains("face"):
				face_mesh = node
	for child in node.get_children():
		_discover_components(child)

func _bind_bones():
	if skeleton == null:
		return
	var count = skeleton.get_bone_count()
	for i in range(count):
		var bname = skeleton.get_bone_name(i).to_lower()
		for key in bone_alias_table.keys():
			if not bone_map.has(key):
				for alias in bone_alias_table[key]:
					if bname == alias or bname.ends_with(alias) or bname.contains(alias):
						bone_map[key] = i
						initial_bone_rotations[i] = skeleton.get_bone_pose_rotation(i)
						break

func _bind_secondary_bones():
	if skeleton == null:
		return
	var count = skeleton.get_bone_count()
	for i in range(count):
		var bname = skeleton.get_bone_name(i).to_lower()
		if bname.contains("hair") or bname.contains("bust") or bname.contains("tail") or bname.contains("skirt") or bname.contains("sec"):
			secondary_bones.append(i)
			secondary_velocities[i] = Vector3.ZERO
			secondary_offsets[i] = Vector3.ZERO
			if not initial_bone_rotations.has(i):
				initial_bone_rotations[i] = skeleton.get_bone_pose_rotation(i)

func _process(delta: float):
	idle_timer += delta
	_update_blinking(delta)
	_update_speech(delta)
	_update_emotions(delta)
	_update_locomotion(delta)
	_update_gestures(delta)
	_update_look_at(delta)
	_update_secondary_physics(delta)

func _update_blinking(delta: float):
	blink_timer += delta
	if not is_blinking:
		if blink_timer >= next_blink_interval:
			is_blinking = true
			blink_progress = 0.0
			blink_timer = 0.0
			next_blink_interval = randf_range(2.5, 6.0)
	else:
		blink_progress += delta * 8.0
		var weight = sin(clamp(blink_progress, 0.0, 1.0) * PI)
		_set_raw_blendshape("blink", weight)
		_set_raw_blendshape("eyeblinkleft", weight)
		_set_raw_blendshape("eyeblinkright", weight)
		_set_raw_blendshape("fcl_eye_close", weight)
		if blink_progress >= 1.0:
			is_blinking = false
			_set_raw_blendshape("blink", 0.0)
			_set_raw_blendshape("eyeblinkleft", 0.0)
			_set_raw_blendshape("eyeblinkright", 0.0)

func _update_speech(delta: float):
	if not is_speaking:
		return
	speech_timer += delta * 12.0
	var vowel_val = abs(sin(speech_timer)) * 0.75 + sin(speech_timer * 0.5) * 0.15
	_set_raw_blendshape("aa", vowel_val)
	_set_raw_blendshape("jawopen", vowel_val * 0.8)
	_set_raw_blendshape("mouthopen", vowel_val)
	_set_raw_blendshape("fcl_mth_a", vowel_val)

func _update_emotions(delta: float):
	for key in target_emotions.keys():
		var target_w = target_emotions[key]
		var cur_w = current_emotions.get(key, 0.0)
		var new_w = lerpf(cur_w, target_w, delta * 8.0)
		current_emotions[key] = new_w
		_apply_emotion_weights(key, new_w)

func _apply_emotion_weights(emotion: String, weight: float):
	var em = emotion.to_lower()
	if em == "happy" or em == "joy":
		_set_raw_blendshape("mouthsmileleft", weight * 0.85)
		_set_raw_blendshape("mouthsmileright", weight * 0.85)
		_set_raw_blendshape("cheeksquintleft", weight * 0.5)
		_set_raw_blendshape("cheeksquintright", weight * 0.5)
		_set_raw_blendshape("fcl_all_joy", weight * 0.9)
	elif em == "sad" or em == "sorrow":
		_set_raw_blendshape("mouthfrownleft", weight * 0.7)
		_set_raw_blendshape("mouthfrownright", weight * 0.7)
		_set_raw_blendshape("browdownleft", weight * 0.6)
		_set_raw_blendshape("browdownright", weight * 0.6)
		_set_raw_blendshape("fcl_all_sorrow", weight * 0.9)
	elif em == "angry" or em == "pout":
		_set_raw_blendshape("browdownleft", weight * 0.8)
		_set_raw_blendshape("browdownright", weight * 0.8)
		_set_raw_blendshape("mouthfrownleft", weight * 0.5)
		_set_raw_blendshape("mouthfrownright", weight * 0.5)
		_set_raw_blendshape("fcl_all_angry", weight * 0.8)
	elif em == "surprised":
		_set_raw_blendshape("eyewideleft", weight * 0.8)
		_set_raw_blendshape("eyewideright", weight * 0.8)
		_set_raw_blendshape("jawopen", weight * 0.4)
		_set_raw_blendshape("fcl_eye_surprised", weight * 0.9)

func _set_raw_blendshape(shape_name: String, weight: float):
	if face_mesh == null or face_mesh.mesh == null:
		return
	var mesh = face_mesh.mesh
	var count = mesh.get_blend_shape_count()
	var target = shape_name.to_lower()
	for i in range(count):
		var bname = mesh.get_blend_shape_name(i).to_lower()
		if bname == target or bname.contains(target):
			face_mesh.set_blend_shape_value(i, clamp(weight, 0.0, 1.0))

func _update_locomotion(delta: float):
	if skeleton == null:
		return
	if is_walking:
		walk_phase += delta * 4.4 * walk_speed
		var hip_idx = bone_map.get("hips", -1)
		if hip_idx != -1:
			var rest_rot = initial_bone_rotations.get(hip_idx, Quaternion.IDENTITY)
			var y_bob = sin(walk_phase * 2.0) * 0.02
			var roll = sin(walk_phase) * 0.04 * float(walk_direction)
			var rot_delta = Quaternion(Vector3.FORWARD, roll) * Quaternion(Vector3.UP, sin(walk_phase) * 0.03)
			skeleton.set_bone_pose_rotation(hip_idx, rest_rot * rot_delta)
			var orig_pos = skeleton.get_bone_rest(hip_idx).origin
			skeleton.set_bone_pose_position(hip_idx, orig_pos + Vector3(0, y_bob, 0))
		
		var l_uleg = bone_map.get("left_upper_leg", -1)
		var l_lleg = bone_map.get("left_lower_leg", -1)
		var r_uleg = bone_map.get("right_upper_leg", -1)
		var r_lleg = bone_map.get("right_lower_leg", -1)
		
		var left_leg_angle = sin(walk_phase) * 0.42
		var right_leg_angle = -sin(walk_phase) * 0.42
		var left_knee_angle = max(0.0, -sin(walk_phase)) * 0.55
		var right_knee_angle = max(0.0, sin(walk_phase)) * 0.55
		
		if l_uleg != -1:
			var r = initial_bone_rotations.get(l_uleg, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(l_uleg, r * Quaternion(Vector3.RIGHT, left_leg_angle))
		if l_lleg != -1:
			var r = initial_bone_rotations.get(l_lleg, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(l_lleg, r * Quaternion(Vector3.RIGHT, left_knee_angle))
		if r_uleg != -1:
			var r = initial_bone_rotations.get(r_uleg, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(r_uleg, r * Quaternion(Vector3.RIGHT, right_leg_angle))
		if r_lleg != -1:
			var r = initial_bone_rotations.get(r_lleg, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(r_lleg, r * Quaternion(Vector3.RIGHT, right_knee_angle))
		
		if active_gesture == "":
			var l_uarm = bone_map.get("left_upper_arm", -1)
			var r_uarm = bone_map.get("right_upper_arm", -1)
			if l_uarm != -1:
				var r = initial_bone_rotations.get(l_uarm, Quaternion.IDENTITY)
				skeleton.set_bone_pose_rotation(l_uarm, r * Quaternion(Vector3.RIGHT, -sin(walk_phase) * 0.3))
			if r_uarm != -1:
				var r = initial_bone_rotations.get(r_uarm, Quaternion.IDENTITY)
				skeleton.set_bone_pose_rotation(r_uarm, r * Quaternion(Vector3.RIGHT, sin(walk_phase) * 0.3))
	else:
		var spine_idx = bone_map.get("spine", -1)
		var chest_idx = bone_map.get("chest", -1)
		var breathe = sin(idle_timer * 1.8) * 0.018
		if spine_idx != -1:
			var r = initial_bone_rotations.get(spine_idx, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(spine_idx, r * Quaternion(Vector3.RIGHT, breathe))
		if chest_idx != -1:
			var r = initial_bone_rotations.get(chest_idx, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(chest_idx, r * Quaternion(Vector3.RIGHT, breathe * 0.8))

func _update_gestures(delta: float):
	if skeleton == null or active_gesture == "":
		return
	gesture_timer += delta
	var t = clamp(gesture_timer / gesture_duration, 0.0, 1.0)
	var envelope = sin(t * PI)
	
	if active_gesture == "wave":
		var r_uarm = bone_map.get("right_upper_arm", -1)
		var r_larm = bone_map.get("right_lower_arm", -1)
		var r_hand = bone_map.get("right_hand", -1)
		if r_uarm != -1:
			var r = initial_bone_rotations.get(r_uarm, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(r_uarm, r * Quaternion(Vector3.FORWARD, -1.2 * envelope) * Quaternion(Vector3.UP, 0.4 * envelope))
		if r_larm != -1:
			var r = initial_bone_rotations.get(r_larm, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(r_larm, r * Quaternion(Vector3.RIGHT, 1.1 * envelope))
		if r_hand != -1:
			var r = initial_bone_rotations.get(r_hand, Quaternion.IDENTITY)
			var wave_sway = sin(gesture_timer * 9.0) * 0.35 * envelope
			skeleton.set_bone_pose_rotation(r_hand, r * Quaternion(Vector3.FORWARD, wave_sway))
	elif active_gesture == "bow":
		var spine_idx = bone_map.get("spine", -1)
		if spine_idx != -1:
			var r = initial_bone_rotations.get(spine_idx, Quaternion.IDENTITY)
			skeleton.set_bone_pose_rotation(spine_idx, r * Quaternion(Vector3.RIGHT, 0.35 * envelope))
	
	if gesture_timer >= gesture_duration:
		var finished = active_gesture
		active_gesture = ""
		gesture_timer = 0.0
		gesture_finished_signal.emit(finished)

func _update_look_at(delta: float):
	if skeleton == null:
		return
	current_look = current_look.lerp(target_look, delta * 5.0)
	var head_idx = bone_map.get("head", -1)
	var neck_idx = bone_map.get("neck", -1)
	var yaw = clamp(-current_look.x * 0.35, -0.45, 0.45)
	var pitch = clamp(-current_look.y * 0.25, -0.3, 0.3)
	
	if head_idx != -1:
		var r = initial_bone_rotations.get(head_idx, Quaternion.IDENTITY)
		var delta_rot = Quaternion(Vector3.UP, yaw * 0.7) * Quaternion(Vector3.RIGHT, pitch * 0.7)
		skeleton.set_bone_pose_rotation(head_idx, r * delta_rot)
	if neck_idx != -1:
		var r = initial_bone_rotations.get(neck_idx, Quaternion.IDENTITY)
		var delta_rot = Quaternion(Vector3.UP, yaw * 0.3) * Quaternion(Vector3.RIGHT, pitch * 0.3)
		skeleton.set_bone_pose_rotation(neck_idx, r * delta_rot)

func _update_secondary_physics(delta: float):
	if skeleton == null or secondary_bones.is_empty():
		return
	var stiffness = 45.0
	var damping = 7.5
	var sway_force = Vector3.ZERO
	if is_walking:
		sway_force = Vector3(sin(walk_phase) * 0.08, 0, cos(walk_phase) * 0.05)
	
	for b in secondary_bones:
		var vel: Vector3 = secondary_velocities[b]
		var offset: Vector3 = secondary_offsets[b]
		var spring_force = -offset * stiffness - vel * damping + sway_force
		vel += spring_force * delta
		offset += vel * delta
		secondary_velocities[b] = vel
		secondary_offsets[b] = offset
		
		var rest_rot = initial_bone_rotations.get(b, Quaternion.IDENTITY)
		var delta_q = Quaternion(Vector3.RIGHT, offset.z) * Quaternion(Vector3.FORWARD, offset.x)
		skeleton.set_bone_pose_rotation(b, rest_rot * delta_q)

func set_locomotion(active: bool, speed: float = 1.0, direction: int = 1):
	is_walking = active
	walk_speed = max(0.1, speed)
	walk_direction = 1 if direction >= 0 else -1

func play_gesture(gesture_name: String, duration: float = 2.2):
	active_gesture = gesture_name.to_lower()
	gesture_timer = 0.0
	gesture_duration = max(0.5, duration)

func set_emotion(name: String, weight: float = 1.0):
	target_emotions[name.to_lower()] = clamp(weight, 0.0, 1.0)

func set_speaking(speaking: bool):
	is_speaking = speaking
	if not speaking:
		speech_timer = 0.0
		_set_raw_blendshape("aa", 0.0)
		_set_raw_blendshape("jawopen", 0.0)
		_set_raw_blendshape("mouthopen", 0.0)

func look_at_normalized(x: float, y: float):
	target_look = Vector2(clamp(x, -1.0, 1.0), clamp(y, -1.0, 1.0))
