import os
import threading
import http.server
import socketserver
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QContextMenuEvent

from core.vrm_bridge import VRMBridge

class ThreadedHTTPServer:
    def __init__(self, port, directory):
        self.port = port
        self.directory = directory
        self.httpd = None
        self.thread = None

    def start(self):
        directory_to_serve = self.directory

        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory_to_serve, **kwargs)

            def log_message(self, format, *args):
                pass

            def end_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                super().end_headers()

            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True

        self.httpd = ThreadedTCPServer(("", self.port), CustomHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass

class VRMWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[VRM JS ({sourceID}:{lineNumber})] {message}", flush=True)

class VRMWidget(QWidget):
    clicked_signal = pyqtSignal()
    avatar_clicked = pyqtSignal(str, float, float)
    gesture_event = pyqtSignal(str, str)
    animation_started = pyqtSignal(str, float)
    animation_finished = pyqtSignal(str)
    
    def __init__(self, parent=None, model_path="/ui/static/vrm_models/Vanessa_Flagship_Anime.vrm"):
        super().__init__(parent)
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        from core.docker_engine_manager import DockerEngineManager
        self.docker_mgr = DockerEngineManager(self.project_root)
        self.server = None
        self.port = 8899

        if not self.docker_mgr.is_port_in_use(8899):
            self.docker_mgr.start_engine()

        if not self.docker_mgr.is_port_in_use(8899):
            for p in range(8899, 8915):
                try:
                    srv = ThreadedHTTPServer(p, self.project_root)
                    srv.start()
                    self.server = srv
                    self.port = p
                    break
                except Exception:
                    continue

        try:
            from core.avatar_directive_server import AvatarDirectiveServer
            AvatarDirectiveServer.get_instance().start()
        except Exception:
            pass

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.webview = QWebEngineView(self)
        self.custom_page = VRMWebEnginePage(self.webview)
        self.webview.setPage(self.custom_page)
        self.webview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.webview.setStyleSheet("background: transparent; border: none;")
        self.webview.page().setBackgroundColor(QColor(0, 0, 0, 0))
        
        profile = self.webview.page().profile()
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self.layout.addWidget(self.webview)
        self.webview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.webview.customContextMenuRequested.connect(self._on_custom_context_menu)
        self.webview.show()

        self.channel = QWebChannel(self.webview.page())
        self.bridge = VRMBridge(self)
        self.bridge.set_page(self.webview.page())
        self.bridge.avatar_clicked.connect(self.avatar_clicked.emit)
        self.bridge.gesture_event.connect(self.gesture_event.emit)
        self.bridge.animation_started.connect(self.animation_started.emit)
        self.bridge.animation_finished.connect(self.animation_finished.emit)
        self.channel.registerObject("vrmBridge", self.bridge)
        self.webview.page().setWebChannel(self.channel)

        self.webview.loadStarted.connect(lambda: print(f"[VRMWebEngine] loadStarted: {self.webview.url().toString()}", flush=True))
        self.webview.loadProgress.connect(lambda p: print(f"[VRMWebEngine] loadProgress: {p}%", flush=True))
        self.webview.loadFinished.connect(lambda ok: print(f"[VRMWebEngine] loadFinished: {ok}, url: {self.webview.url().toString()}", flush=True))

        self.default_model_path = model_path
        url_path = self._get_url_for_path(model_path)
        full_url = f"http://127.0.0.1:{self.port}/ui/vrm/index.html?model={url_path}"
        print(f"[VRMWebEngine] Calling load with: {full_url}", flush=True)
        self.webview.load(QUrl(full_url))

    def _get_url_for_path(self, model_path: str) -> str:
        url_path = model_path
        if os.path.isabs(model_path):
            try:
                if not model_path.startswith(self.project_root):
                    custom_dir = os.path.join(self.project_root, "ui/static/vrm_models/custom")
                    os.makedirs(custom_dir, exist_ok=True)
                    fname = os.path.basename(model_path)
                    dest_path = os.path.join(custom_dir, fname)
                    if not os.path.exists(dest_path) or os.path.getsize(dest_path) != os.path.getsize(model_path):
                        import shutil
                        shutil.copy2(model_path, dest_path)
                    rel = os.path.relpath(dest_path, self.project_root)
                else:
                    rel = os.path.relpath(model_path, self.project_root)
                url_path = "/" + rel.replace("\\", "/")
            except Exception as e:
                print(f"[VRMWidget] Error preparing model path {model_path}: {e}")
                url_path = model_path
        return url_path

    def _run_js_safe(self, code: str):
        if not hasattr(self, "webview") or not self.webview:
            return
        page = self.webview.page()
        if not page:
            return
        QTimer.singleShot(0, lambda: page.runJavaScript(code))

    def load_model(self, model_path: str):
        url_path = self._get_url_for_path(model_path)
        self._run_js_safe(f"window.vrmController && window.vrmController.setModel('{url_path}');")

    def set_speaking(self, is_speaking: bool):
        if is_speaking:
            self.bridge.start_talking()
        else:
            self.bridge.stop_talking()

    def set_expression(self, name: str, weight: float = 1.0):
        self.bridge.set_expression(name, weight)

    def set_morph_target(self, name: str, weight: float = 1.0):
        self.bridge.set_morph_target(name, weight)

    def set_emotion(self, mood: str, weight: float = 1.0):
        self.bridge.set_expression(mood, weight)

    def start_motion(self, motion_name: str):
        self._run_js_safe(f"window.vrmController && window.vrmController.playMotion('{motion_name}');")

    def send_motor_intent(self, intent: str, vx: float = 0.0, vy: float = 0.0, speed: float = 1.0, mood: str = "neutral", posture: str = "standby"):
        self.bridge.dispatch_motor_command(intent, vx, vy, speed, mood, posture)

    def dispatch_sensory_event(self, payload: dict):
        import json
        raw = json.dumps(payload, ensure_ascii=False)
        self._run_js_safe(f"window.vrmController && window.vrmController.onSensoryEvent && window.vrmController.onSensoryEvent({raw});")

    def _js(self, code: str):
        self._run_js_safe(f"window.vrmController && ({code});")

    def play_gesture(self, name: str):
        safe = "".join(c for c in name if c.isalnum() or c == "_")
        self._js(f"window.vrmController.playGesture && window.vrmController.playGesture('{safe}')")

    def start_walking(self, direction: int = 1, speed: float = 1.0):
        self._js(f"window.vrmController.startWalking && window.vrmController.startWalking({1 if direction >= 0 else -1}, {float(speed):.2f})")

    def stop_walking(self):
        self._js("window.vrmController.stopWalking && window.vrmController.stopWalking()")

    def set_persona_mood(self, mood: str):
        safe = "".join(c for c in mood if c.isalnum() or c == "_")
        self._js(f"window.vrmController.setPersonaMood && window.vrmController.setPersonaMood('{safe}')")

    def set_walk_speed(self, speed_ratio: float = 1.0):
        self._run_js_safe(f"window.vrmController && window.vrmController.setWalkSpeed && window.vrmController.setWalkSpeed({float(speed_ratio):.2f});")

    def set_body_facing(self, yaw_radians: float, turn_speed: float = 5.0):
        self._run_js_safe(f"window.vrmController && window.vrmController.setBodyFacing && window.vrmController.setBodyFacing({float(yaw_radians):.3f}, {float(turn_speed):.2f});")

    def play_standby_pose(self):
        self._run_js_safe(f"window.vrmController && window.vrmController.playNextStandbyPose && window.vrmController.playNextStandbyPose();")

    def play_playful_motion(self):
        self._run_js_safe(f"window.vrmController && window.vrmController.playNextPlayfulMotion && window.vrmController.playNextPlayfulMotion();")

    def set_music_active(self, active: bool, bpm: float = 120.0):
        js_bool = "true" if active else "false"
        self._run_js_safe(f"window.vrmController && window.vrmController.setMusicActive({js_bool}, {bpm});")

    def set_music_genre(self, genre: str = "pop", bpm: float = 120.0):
        self._run_js_safe(f"window.vrmController && window.vrmController.setMusicGenre && window.vrmController.setMusicGenre('{genre}', {bpm});")

    def look_at(self, x: float, y: float):
        self._run_js_safe(f"window.vrmController && window.vrmController.lookAt({x}, {y});")

    def set_opacity(self, alpha: float):
        self.setWindowOpacity(alpha)

    def frame_avatar(self):
        self._js("window.vrmController && window.vrmController.frameAvatar && window.vrmController.frameAvatar()")

    def set_perched(self, perched: bool, perch_style: str = "sit"):
        js_bool = "true" if perched else "false"
        safe_style = "".join(c for c in perch_style if c.isalnum() or c == "_")
        self._js(f"window.vrmController && window.vrmController.setPerched && window.vrmController.setPerched({js_bool}, '{safe_style}')")

    def set_avatar_mode(self, mode: str = "standard"):
        safe_mode = "".join(c for c in mode if c.isalnum() or c == "_")
        self._js(f"window.vrmController && window.vrmController.setAvatarMode && window.vrmController.setAvatarMode('{safe_mode}')")

    def set_throttling(self, throttled: bool = False, fps: float = 15.0):
        js_bool = "true" if throttled else "false"
        self._js(f"window.vrmController && window.vrmController.setThrottling && window.vrmController.setThrottling({js_bool}, {float(fps):.1f})")

    def notify_activity(self, state: str = "action"):
        safe_state = "".join(c for c in state if c.isalnum() or c == "_")
        self._js(f"window.vrmController && window.vrmController.notifyActivity && window.vrmController.notifyActivity('{safe_state}')")

    head_pat_signal = pyqtSignal()
    body_click_signal = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked_signal.emit()
        if event.pos().y() < (self.height() * 0.45):
            self.head_pat_signal.emit()
            self.start_motion("pat_head")
        else:
            self.body_click_signal.emit()
        super().mousePressEvent(event)

    def _on_custom_context_menu(self, pos):
        global_pos = self.webview.mapToGlobal(pos)
        parent = self.parent()
        while parent:
            if hasattr(parent, "contextMenuEvent"):
                local_pos = parent.mapFromGlobal(global_pos)
                ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, local_pos, global_pos)
                parent.contextMenuEvent(ev)
                break
            parent = parent.parent()

    def send_canonical_command_packet(self, packet: dict):
        import json
        payload = json.dumps(packet)
        self._run_js_safe(f"window.vrmController && window.vrmController.applyCanonicalCommandPacket && window.vrmController.applyCanonicalCommandPacket({payload});")

    def apply_conscious_skeletal_packet(self, packet: dict):
        import json
        payload = json.dumps(packet)
        self._run_js_safe(f"window.vrmController && window.vrmController.applyConsciousSkeletalPacket && window.vrmController.applyConsciousSkeletalPacket({payload});")

    def apply_external_physics_impulse(self, dx: float, dy: float, dt: float = 0.016):
        self._run_js_safe(f"window.vrmController && window.vrmController.applyExternalPhysicsImpulse && window.vrmController.applyExternalPhysicsImpulse({float(dx):.4f}, {float(dy):.4f}, {float(dt):.4f});")

    def set_spring_profile(self, profile: str):
        safe_profile = "".join(c for c in profile if c.isalnum() or c == "_")
        self._run_js_safe(f"window.vrmController && window.vrmController.setSpringProfile && window.vrmController.setSpringProfile('{safe_profile}');")

    def set_asymmetric_expression(self, preset: str, intensity: float = 1.0):
        safe_preset = "".join(c for c in preset if c.isalnum() or c == "_")
        self._run_js_safe(f"window.vrmController && window.vrmController.setAsymmetricFacialPreset && window.vrmController.setAsymmetricFacialPreset('{safe_preset}', {float(intensity):.2f});")

    def set_directive(self, directive: dict):
        import json
        payload = json.dumps(directive)
        self._run_js_safe(f"window.vrmController && window.vrmController.setDirective && window.vrmController.setDirective({payload});")

    def closeEvent(self, event):
        if self.server:
            self.server.stop()
        try:
            from core.avatar_directive_server import AvatarDirectiveServer
            AvatarDirectiveServer.get_instance().stop()
        except Exception:
            pass
        super().closeEvent(event)
