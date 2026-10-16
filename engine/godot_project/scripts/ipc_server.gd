extends Node
class_name GodotIPCServer

signal command_received(cmd: String, data: Dictionary)

@export var port: int = 8998
@export var avatar_rig: Node = null

var tcp_server: TCPServer = null
var clients: Array[StreamPeerTCP] = []
var read_buffers: Dictionary = {}

func _ready():
	tcp_server = TCPServer.new()
	var err = tcp_server.listen(port, "127.0.0.1")
	if err != OK:
		for p in range(8999, 9020):
			err = tcp_server.listen(p, "127.0.0.1")
			if err == OK:
				port = p
				break
	
	if avatar_rig != null:
		avatar_rig.model_loaded_signal.connect(_on_model_loaded)
		avatar_rig.gesture_finished_signal.connect(_on_gesture_finished)

func _process(_delta: float):
	if tcp_server != null and tcp_server.is_connection_available():
		var client = tcp_server.take_connection()
		if client != null:
			clients.append(client)
			read_buffers[client] = ""
			send_to_client(client, {"event": "connected", "port": port})
	
	var i = clients.size() - 1
	while i >= 0:
		var client = clients[i]
		client.poll()
		var status = client.get_status()
		if status == StreamPeerTCP.STATUS_ERROR or status == StreamPeerTCP.STATUS_NONE:
			read_buffers.erase(client)
			clients.remove_at(i)
		elif status == StreamPeerTCP.STATUS_CONNECTED:
			var bytes_avail = client.get_available_bytes()
			if bytes_avail > 0:
				var chunk = client.get_utf8_string(bytes_avail)
				var buf = read_buffers.get(client, "") + chunk
				var lines = buf.split("\n")
				read_buffers[client] = lines[-1]
				for idx in range(lines.size() - 1):
					var line = lines[idx].strip_edges()
					if line != "":
						_handle_incoming_json(client, line)
		i -= 1

func _handle_incoming_json(client: StreamPeerTCP, raw: String):
	var parsed = JSON.parse_string(raw)
	if typeof(parsed) != TYPE_DICTIONARY:
		return
	var cmd = parsed.get("cmd", "")
	command_received.emit(cmd, parsed)
	
	if cmd == "ping":
		send_to_client(client, {"event": "pong"})
	elif cmd == "load_model":
		var path = parsed.get("path", "")
		if avatar_rig != null and path != "":
			var ok = avatar_rig.load_model(path)
			send_to_client(client, {"event": "load_result", "success": ok, "path": path})
	elif cmd == "start_walking":
		var spd = float(parsed.get("speed", 1.0))
		var dir = int(parsed.get("dir", 1))
		if avatar_rig != null:
			avatar_rig.set_locomotion(true, spd, dir)
	elif cmd == "stop_walking":
		if avatar_rig != null:
			avatar_rig.set_locomotion(false)
	elif cmd == "set_emotion":
		var name = str(parsed.get("name", "neutral"))
		var w = float(parsed.get("weight", 1.0))
		if avatar_rig != null:
			avatar_rig.set_emotion(name, w)
	elif cmd == "set_speaking":
		var speaking = bool(parsed.get("is_speaking", false))
		if avatar_rig != null:
			avatar_rig.set_speaking(speaking)
	elif cmd == "play_gesture":
		var name = str(parsed.get("name", ""))
		var dur = float(parsed.get("duration", 2.2))
		if avatar_rig != null:
			avatar_rig.play_gesture(name, dur)
	elif cmd == "look_at":
		var x = float(parsed.get("x", 0.0))
		var y = float(parsed.get("y", 0.0))
		if avatar_rig != null:
			avatar_rig.look_at_normalized(x, y)

func broadcast(data: Dictionary):
	var line = JSON.stringify(data) + "\n"
	for client in clients:
		if client.get_status() == StreamPeerTCP.STATUS_CONNECTED:
			client.put_utf8_string(line)

func send_to_client(client: StreamPeerTCP, data: Dictionary):
	if client.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		var line = JSON.stringify(data) + "\n"
		client.put_utf8_string(line)

func _on_model_loaded(mname: String):
	broadcast({"event": "model_loaded", "name": mname})

func _on_gesture_finished(gname: String):
	broadcast({"event": "animation_finished", "name": gname})
