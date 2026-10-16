import threading
import asyncio
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from core.action_parser import parse_actions_and_clean_speech


class VanessaIPCHandler(QObject):
    def __init__(self, overlay, server_name: str = "vanessa_overlay_ipc"):
        super().__init__(overlay)
        self.overlay = overlay
        self.server_name = server_name
        self.server = QLocalServer(self)
        self._start_server()

    def _start_server(self):
        try:
            self.server.removeServer(self.server_name)
            self.server.newConnection.connect(self._on_new_connection)
            if self.server.listen(self.server_name):
                print(f"[IPC] Servidor iniciado en socket: {self.server_name}")
            else:
                print(f"[IPC] Error iniciando servidor en socket: {self.server_name}")
        except Exception as e:
            print(f"[IPC] Error al iniciar socket IPC: {e}")

    def _on_new_connection(self):
        socket = self.server.nextPendingConnection()
        if socket:
            if not hasattr(self, "_active_clients"):
                self._active_clients = set()
            self._active_clients.add(socket)
            socket.readyRead.connect(lambda s=socket: self._on_socket_ready(s))
            socket.disconnected.connect(lambda s=socket: self._on_socket_disconnected(s))
            if socket.bytesAvailable() > 0:
                self._on_socket_ready(socket)

    def _on_socket_ready(self, socket: QLocalSocket):
        try:
            if socket and socket.isValid() and socket.bytesAvailable() > 0:
                self._process_message(socket)
        except Exception as e:
            print(f"[IPC] Error leyendo socket: {e}")

    def _on_socket_disconnected(self, socket: QLocalSocket):
        try:
            if hasattr(self, "_active_clients"):
                self._active_clients.discard(socket)
            socket.deleteLater()
        except Exception:
            pass

    def _process_message(self, socket: QLocalSocket):
        try:
            raw = bytes(socket.readAll()).decode('utf-8', errors='ignore').strip()
            print(f"[IPC] Mensaje recibido: {raw}")
            overlay = self.overlay

            if raw.startswith("{"):
                import json
                try:
                    data = json.loads(raw)
                    if data.get("type") == "action" or "action" in data:
                        act_payload = data.get("data", data)
                        QTimer.singleShot(0, lambda p=act_payload: overlay.on_voice_action(p))
                        socket.write(b"ok\n")
                        socket.flush()
                        return
                    elif data.get("type") in ("command", "voice_command", "text_command") or "command" in data:
                        cmd_text = data.get("command") or data.get("text", "")
                        if hasattr(overlay, "voice_worker") and overlay.voice_worker:
                            QTimer.singleShot(0, lambda t=cmd_text: overlay.voice_worker.on_continuous_speech(t, True, 99.0))
                        socket.write(b"dispatched\n")
                        socket.flush()
                        return
                    elif data.get("type") == "gesture" or "gesture" in data:
                        g = data.get("gesture", data.get("data", {}).get("gesture", ""))
                        QTimer.singleShot(0, lambda gg=g: overlay.vrm_widget.play_gesture(gg))
                        socket.write(b"ok\n")
                        socket.flush()
                        return
                    elif data.get("type") in ("model", "switch_model") or "model" in data:
                        m = data.get("model", "")
                        QTimer.singleShot(0, lambda mm=m: overlay.switch_vrm_model(mm))
                        socket.write(b"ok\n")
                        socket.flush()
                        return
                    elif data.get("type") == "motion" or "motion" in data:
                        m = data.get("motion", data.get("data", {}).get("motion", "idle"))
                        QTimer.singleShot(0, lambda mot=m: overlay.vrm_widget.start_motion(mot))
                        socket.write(b"ok\n")
                        socket.flush()
                        return
                except Exception as ex:
                    print(f"[IPC] JSON decode error: {ex}")

            if "reload_settings" in raw or "settings_updated" in raw:
                QTimer.singleShot(0, overlay.reload_settings_from_memory)
            elif "settings" in raw:
                QTimer.singleShot(0, overlay.open_settings_dialog)
            elif "menu" in raw or "context_menu" in raw:
                QTimer.singleShot(0, overlay.show_context_menu_programmatic)
            elif raw.startswith("gesture:"):
                g = raw.split("gesture:", 1)[1].strip()
                QTimer.singleShot(0, lambda gg=g: overlay.vrm_widget.play_gesture(gg))
            elif raw.startswith("js:"):
                js_code = raw.split("js:", 1)[1].strip()
                QTimer.singleShot(0, lambda code=js_code: overlay.vrm_widget.webview.page().runJavaScript(code))
            elif raw.startswith("media:"):
                op = raw.split("media:", 1)[1].strip()
                QTimer.singleShot(0, lambda o=op: overlay.screen_interact.interactive_press_media(o))
            elif raw.startswith("walk:"):
                tgt = raw.split("walk:", 1)[1].strip()
                QTimer.singleShot(0, overlay.roam_bottom_left if tgt == "left" else overlay.roam_home)
            elif "model:" in raw:
                m = raw.split("model:", 1)[1].strip()
                QTimer.singleShot(0, lambda: overlay.switch_vrm_model(m))
            elif "volume:" in raw:
                v = int(raw.split("volume:", 1)[1].strip())
                QTimer.singleShot(0, lambda: overlay.set_volume(v))
            elif "balloon:" in raw:
                msg = raw.split("balloon:", 1)[1].strip()
                QTimer.singleShot(0, lambda m=msg: overlay.show_balloon(m, duration_ms=8000))
            elif "say:" in raw:
                text_to_say = raw.split("say:", 1)[1].strip()
                clean_text, mot, expr = parse_actions_and_clean_speech(text_to_say)

                if mot or expr:
                    QTimer.singleShot(0, lambda m=mot, e=expr: overlay.on_vrm_action_requested(m or "", e or ""))

                if not clean_text:
                    return

                def _ipc_on_start(t=clean_text):
                    QTimer.singleShot(0, lambda: overlay.show_balloon(f"💬 {t}", duration_ms=10000))
                    QTimer.singleShot(0, lambda: overlay.start_speaking_anim("happy"))

                def _ipc_on_done():
                    QTimer.singleShot(0, overlay.stop_speaking_anim)

                threading.Thread(
                    target=lambda t=clean_text: asyncio.run(
                        overlay.tts.speak(t, mood="happy", on_start=_ipc_on_start, on_done=_ipc_on_done)
                    ),
                    daemon=True
                ).start()
            elif raw.startswith("js:"):
                js_code = raw[3:].strip()
                QTimer.singleShot(0, lambda c=js_code: overlay.vrm_widget.webview.page().runJavaScript(c))
            elif "motion:" in raw:
                m = raw.split("motion:", 1)[1].strip()
                QTimer.singleShot(0, lambda mot=m: overlay.vrm_widget.start_motion(mot))
            elif "tab:new" in raw or "new_tab" in raw:
                QTimer.singleShot(0, lambda: overlay.screen_interact.quick_tab_action("new"))
            elif "tab:close" in raw or "close_tab" in raw:
                QTimer.singleShot(0, lambda: overlay.screen_interact.quick_tab_action("close"))
            elif "media:pause" in raw or "media:play" in raw or "media:toggle" in raw:
                QTimer.singleShot(0, lambda: overlay.interactive_press_media("play_pause"))
            elif "media:next" in raw:
                QTimer.singleShot(0, lambda: overlay.interactive_press_media("next"))
            elif "media:prev" in raw:
                QTimer.singleShot(0, lambda: overlay.interactive_press_media("previous"))
            elif "music:on" in raw or "music:play" in raw:
                QTimer.singleShot(0, lambda: overlay.vrm_widget.set_music_active(True, 128.0))
            elif "music:off" in raw or "music:stop" in raw:
                QTimer.singleShot(0, lambda: overlay.vrm_widget.set_music_active(False))
            elif "perch" in raw:
                QTimer.singleShot(0, lambda: overlay.perch_on_window_border())
            elif "slide" in raw or "scrollbar" in raw:
                QTimer.singleShot(0, lambda: overlay.slide_on_window_scrollbar())
            elif "read" in raw or "learn" in raw:
                QTimer.singleShot(0, lambda: overlay.screen_interact.read_and_learn_context(overlay.screen_interact.get_active_hyprland_window() or {}))
            elif "curious:mouse" in raw or "curious:cursor" in raw:
                QTimer.singleShot(0, lambda: overlay.curious_inspect_screen("cursor"))
            elif "curious" in raw or "point" in raw:
                QTimer.singleShot(0, lambda: overlay.curious_inspect_screen("active_window"))
            elif "text:copy" in raw:
                QTimer.singleShot(0, lambda: overlay.select_and_highlight_text("copy"))
            elif "text:select" in raw or "text:highlight" in raw:
                QTimer.singleShot(0, lambda: overlay.select_and_highlight_text("all"))
            elif "home" in raw:
                QTimer.singleShot(0, overlay.roam_home)
            elif "stroll" in raw:
                QTimer.singleShot(0, overlay.roam_stroll)
            elif "telemetry" in raw:
                QTimer.singleShot(0, overlay.show_telemetry_action)
            elif "weather" in raw or "clima" in raw:
                loc = raw.split(":", 1)[1].strip() if ":" in raw else ""
                QTimer.singleShot(0, lambda l=loc: overlay.show_weather_action(l))
            elif "digest" in raw or "morning_digest" in raw or "briefing" in raw:
                QTimer.singleShot(0, overlay.show_morning_digest_action)
            elif "screenshot" in raw:
                QTimer.singleShot(0, overlay.take_screenshot_action)
            elif "voice:scan" in raw or "audio:find" in raw:
                QTimer.singleShot(0, overlay.search_voice_files_action)
            elif "hud" in raw:
                QTimer.singleShot(0, overlay.open_jarvis_hud_action)
            elif "cycle_outfit" in raw or "next_outfit" in raw or "outfit" in raw:
                QTimer.singleShot(0, overlay.cycle_next_outfit)
            elif "protocol:" in raw:
                prot = raw.split("protocol:", 1)[1].strip()
                def _run_prot(p=prot):
                    res = overlay.brain.jarvis.execute_protocol(p)
                    overlay.show_balloon(f"⚡ {res.get('message')}", duration_ms=5000)
                QTimer.singleShot(0, _run_prot)

            socket.write(b"ok\n")
            socket.flush()
        except Exception as e:
            print(f"[IPC] Error procesando comando: {e}")
