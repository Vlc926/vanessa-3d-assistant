import sys
import os
import hashlib
import re
import json
import random
import asyncio
import threading
import subprocess
import math
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QWidget, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QCursor, QPixmap, QPainterPath
)

from core.memory import MemoryManager
from core.learning_vault import LearningVault
from core.system_control import SystemController
from core.file_manager import FileManager
from core.music_detector import MusicDetector
from core.brain import AssistantBrain
from core.os_interact import OSInteractor
from core.anime_tts import AnimeTTS
from senses.speech_to_text import SpeechToText
from senses.voice_biometrics import VoiceAnalyzer
from core.voice_enrollment import VoiceEnrollmentManager
from senses.face_biometrics import FaceBiometrics
from core.proactive_perception import ProactivePerceptionEngine
from core.desktop_physics import DesktopInertiaEngine
from core.environment_perception import EnvironmentPerception
from core.avatar_controller import AvatarLifecycleController
from core.dialogue_emotion_controller import DialogueEmotionController
from core.hypr_interaction_controller import HyprlandInteractionController
from core.conscious_skeletal_controller import ConsciousSkeletalController

from ui.live2d_widget import Live2DWidget
from core.vrm_widget import VRMWidget

from core.action_parser import parse_actions_and_clean_speech
from core.sensory_broker import SensoryBroker
from core.voice_worker import BackgroundVoiceWorker
from core.roaming import RoamingController
from core.screen_interaction import ScreenInteractor
from core.multimedia_tracker import MultimediaTracker
from core.notification_tracker import NotificationTracker
from core.desktop_life import DesktopLifeEngine
from core.ipc_handler import VanessaIPCHandler
from core.remote_bridge import RemoteCloudBridge
from core.protection_protocol import ProtectionProtocolManager
from core.autonomous_life import AutonomousCoexistenceEngine
from ui.context_menu import build_context_menu, show_context_menu_programmatic
from ui.balloon_renderer import BalloonRenderer

from ui.dialogs import (
    GeminiApiKeyDialog,
    VoiceEnrollmentDialog,
    FileLocatorDialog,
    HyprlandWorkspacesDialog,
    VolumeDialog,
)
from ui.settings_dialog import VanessaSettingsDialog
from ui.model_selector_dialog import VanessaModelSelectorDialog
from ui.jarvis_hud import JarvisCyberHUDDialog


class VanessaDesktopOverlay(QWidget):
    def __init__(self):
        super().__init__()

        self.memory = MemoryManager()
        self.learning_vault = LearningVault()
        self.sys_ctrl = SystemController()
        self.file_mgr = FileManager()
        self.music_det = MusicDetector()
        self.os_interact = OSInteractor()
        self.personality_path = "config/personality.json"
        self.brain = AssistantBrain(
            self.memory, self.sys_ctrl, self.file_mgr, self.music_det, self.personality_path
        )

        initial_voice = self.brain.settings.get("voice_settings", {}).get("voice", "dalia_anime")
        voice_mode = self.brain.settings.get("voice_settings", {}).get("mode", "cloud")
        self.vanessa_volume = int(self.brain.settings.get("voice_settings", {}).get("volume", 85))
        self.tts = AnimeTTS(voice=initial_voice, volume=self.vanessa_volume, mode=voice_mode)
        self.stt = SpeechToText(model_size="base", device="cpu", compute_type="int8")
        self.voice_analyzer = VoiceAnalyzer()
        self.voice_mgr = VoiceEnrollmentManager()
        self.face_biometrics = FaceBiometrics()

        self.brain.audio_intel.stt = self.stt
        self.brain.audio_intel.voice_mgr = self.voice_mgr
        self.brain.on_reminder_due = self._on_jarvis_reminder_due

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setWindowTitle("Vanessa Maid")

        self.avatar_type = "vrm"
        self.using_vrm = True
        self.using_live2d = False
        base_dir = os.path.dirname(os.path.abspath(__file__))

        from core.model_optimizer import ModelOptimizer
        optimizer = ModelOptimizer()
        user_catalog = optimizer.get_user_models_catalog()

        self.vrm_models_map = {}
        if "hoshimachi_suisei" in user_catalog:
            self.vrm_models_map["vanessa"] = user_catalog["hoshimachi_suisei"]["pmx_path"]
        for k, item in user_catalog.items():
            self.vrm_models_map[k] = item["pmx_path"]

        alias_map = {
            "suisei": "hoshimachi_suisei",
            "marine": "houshou_marine",
            "korone": "inugami_korone",
            "okayu": "nekomata_okayu",
            "watame": "tsunomaki_watame",
            "kronii": "ouro_kronii",
            "reine": "pavolia_reine",
            "miku": "hatsune_miku_v4c"
        }
        for alias, target in alias_map.items():
            if target in self.vrm_models_map:
                self.vrm_models_map[alias] = self.vrm_models_map[target]

        self.current_vrm_model = self.brain.personality.get("vrm_model", "hoshimachi_suisei")
        if self.current_vrm_model not in self.vrm_models_map:
            self.current_vrm_model = "hoshimachi_suisei"
        initial_vrm_path = self.vrm_models_map.get(
            self.current_vrm_model,
            self.vrm_models_map.get("vanessa", list(self.vrm_models_map.values())[0] if self.vrm_models_map else "")
        )
        engine_type = self.brain.personality.get("engine_3d", "threejs")
        if engine_type == "godot" and os.path.exists(os.path.join(base_dir, "bin/godot")):
            from core.godot_widget import GodotWidget
            self.vrm_widget = GodotWidget(self, model_path=initial_vrm_path, autostart_engine=True)
        else:
            self.vrm_widget = VRMWidget(self, model_path=initial_vrm_path)
        SensoryBroker.get_instance().set_vrm_widget(self.vrm_widget)
        self.vrm_widget.avatar_clicked.connect(self.on_vrm_avatar_clicked)
        self.vrm_widget.animation_finished.connect(self._on_vrm_animation_finished)
        self.vrm_widget.head_pat_signal.connect(self.on_vrm_head_pat)
        self.vrm_widget.body_click_signal.connect(self.on_vrm_body_click)

        self.current_live2d_model = self.brain.personality.get("live2d_model", "hiyori")
        self.live2d_models_map = {
            "hiyori": os.path.join(base_dir, "ui/static/live2d_models/Hiyori/Hiyori.model3.json"),
            "haru": os.path.join(base_dir, "ui/static/live2d_models/Haru/Haru.model3.json"),
            "mao": os.path.join(base_dir, "ui/static/live2d_models/Mao/Mao.model3.json"),
            "rice": os.path.join(base_dir, "ui/static/live2d_models/Rice/Rice.model3.json"),
        }
        initial_live2d_path = self.live2d_models_map.get(
            self.current_live2d_model,
            os.path.join(base_dir, "ui/static/live2d_models/Hiyori/Hiyori.model3.json")
        )
        self.live2d_widget = Live2DWidget(self, model_path=initial_live2d_path)
        self.live2d_widget.clicked_signal.connect(self.on_live2d_clicked)

        self.live2d_widget.hide()
        self.vrm_widget.show()

        saved_size = self.brain.personality.get("avatar_size", {})
        self.current_size_preset = saved_size.get("preset", "medium")
        self.base_width = int(saved_size.get("width", 350))
        self.base_height = int(saved_size.get("height", 580))
        self.avatar_width = int(self.base_width * 0.94)
        self.avatar_height = int(self.base_height * 0.94)

        self.vrm_widget.setGeometry(0, 0, self.base_width, self.base_height)
        self.live2d_widget.setGeometry(0, 0, self.base_width, self.base_height)
        self.resize(self.base_width, self.base_height)
        self.setMinimumSize(220, 320)
        self.setMaximumSize(720, 1080)

        self._can_exit = False
        self.current_alpha = 1.0
        self.current_theme = self.brain.personality.get("theme", "hutao")
        self.anim_state = "idle"
        self.frame_idx = 0
        self.all_frames: List[QPixmap] = []
        self.current_pixmap: Optional[QPixmap] = None
        self.load_animation_frames()

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.next_animation_frame)
        self.anim_timer.start(350)

        self.balloon_text = ""
        self.bubble_rect = QRectF()
        self.combined_balloon_path = QPainterPath()
        self.balloon_timer = QTimer(self)
        self.balloon_timer.setSingleShot(True)
        self.balloon_timer.timeout.connect(self.clear_balloon)

        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.enter_sleep_mode)
        self.inactivity_timer.start(45000)

        self.is_dragging = False
        self.drag_position = QPoint()

        self.roaming = RoamingController(self)
        self.screen_interact = ScreenInteractor(self)
        self.multimedia = MultimediaTracker(self)
        self.notification_tracker = NotificationTracker(self)
        self.notification_tracker.notification_received.connect(self.on_system_notification)
        self.notification_tracker.start_monitoring()
        self.proactive_engine = ProactivePerceptionEngine(self.memory, self.brain, self.os_interact)
        self.desktop_life = DesktopLifeEngine(self)

        self.proactive_engine.reaction_signal.connect(self.desktop_life.on_proactive_reaction)
        self.proactive_engine.thought_signal.connect(self.desktop_life.on_proactive_thought)
        self.proactive_engine.roam_signal.connect(self.roaming.on_proactive_roam)
        self.proactive_engine.voice_only_signal.connect(self.desktop_life.on_voice_only_reaction)
        self.proactive_engine.spontaneous_emotion_signal.connect(self.desktop_life.on_spontaneous_emotion)

        self.remote_bridge = RemoteCloudBridge(parent=self)
        self.remote_bridge.connection_changed.connect(self._on_remote_connection_changed)
        self.remote_bridge.omni_notification.connect(self._on_remote_omni_notification)
        self.remote_bridge.start()

        screens = QApplication.screens()
        screen_geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = screen_geom.width()
        sh = screen_geom.height()
        init_x = sw - self.base_width - 45
        init_y = sh - self.base_height - 65
        self.move(init_x, init_y)
        self.anchor_bottom_right = QPoint(init_x + self.base_width, init_y + self.base_height)
        self._recalculate_responsive_layout()
        QTimer.singleShot(400, lambda: self.sync_hyprland_position(self.x(), self.y()))

        self._last_avatar_interaction_time = 0.0
        self.voice_worker = None
        QTimer.singleShot(250, self.init_voice_worker)

        self._last_persona_mood = None
        self.persona_timer = QTimer(self)
        self.persona_timer.timeout.connect(self._persona_tick)
        self.persona_timer.start(20000)
        QTimer.singleShot(4000, self._persona_tick)

        self._last_gaze_pos = (0.0, 0.0)
        self.mouse_tracking_timer = QTimer(self)
        self.mouse_tracking_timer.timeout.connect(self._track_cursor_gaze)
        self.mouse_tracking_timer.start(50)

        self.ipc_handler = VanessaIPCHandler(self)

        self.sys_ctrl.show_desktop_notification(
            "Vanessa Activa",
            "A su completo servicio, Amo Víctor. Clic derecho sobre mí para opciones."
        )
        self.physics_engine = DesktopInertiaEngine(self)
        self.perception_engine = EnvironmentPerception(self)
        self.perception_engine.start()
        self.perception_daemon = self.perception_engine
        self.avatar_controller = AvatarLifecycleController(self)
        self.dialogue_controller = DialogueEmotionController(self)
        self.hypr_controller = HyprlandInteractionController(self)
        self.protection_protocol = ProtectionProtocolManager(self)
        self.autonomous_coexistence = AutonomousCoexistenceEngine(self)
        self.skeletal_controller = ConsciousSkeletalController(self)

    @property
    def is_roaming(self) -> bool:
        return self.roaming.is_roaming

    @is_roaming.setter
    def is_roaming(self, val: bool):
        self.roaming.is_roaming = val

    @property
    def autonomous_roaming_enabled(self) -> bool:
        return self.roaming.autonomous_roaming_enabled

    @autonomous_roaming_enabled.setter
    def autonomous_roaming_enabled(self, val: bool):
        self.roaming.autonomous_roaming_enabled = val

    @property
    def autonomous_life_enabled(self) -> bool:
        return self.desktop_life.autonomous_life_enabled

    @autonomous_life_enabled.setter
    def autonomous_life_enabled(self, val: bool):
        self.desktop_life.autonomous_life_enabled = val

    @property
    def current_media_playing(self) -> bool:
        return self.multimedia.current_media_playing

    @current_media_playing.setter
    def current_media_playing(self, val: bool):
        self.multimedia.current_media_playing = val

    @property
    def mouse_tracking_enabled(self) -> bool:
        return self.screen_interact.mouse_tracking_enabled

    @mouse_tracking_enabled.setter
    def mouse_tracking_enabled(self, val: bool):
        self.screen_interact.mouse_tracking_enabled = val

    def smooth_roam_to(self, *args, **kwargs):
        return self.roaming.smooth_roam_to(*args, **kwargs)

    def roam_home(self):
        return self.roaming.roam_home()

    def roam_bottom_left(self):
        return self.roaming.roam_bottom_left()

    def roam_top_right(self):
        return self.roaming.roam_top_right()

    def roam_follow_active_window(self):
        return self.roaming.roam_follow_active_window()

    def roam_stroll(self):
        return self.roaming.roam_stroll()

    def toggle_autonomous_roaming(self):
        return self.roaming.toggle_autonomous_roaming()

    def interactive_press_media(self, action: str = "play_pause", media_type: str = "auto"):
        return self.screen_interact.interactive_press_media(action, media_type=media_type)

    def curious_inspect_screen(self, target_type: str = "active_window"):
        return self.screen_interact.curious_inspect_screen(target_type)

    def perch_on_window_border(self, *args, **kwargs):
        return self.screen_interact.perch_on_window_border(*args, **kwargs)

    def slide_on_window_scrollbar(self, *args, **kwargs):
        return self.screen_interact.slide_on_window_scrollbar(*args, **kwargs)

    def unperch_and_roam_home(self):
        return self.screen_interact.unperch_and_roam_home()

    def select_and_highlight_text(self, mode: str = "all"):
        return self.screen_interact.select_and_highlight_text(mode)

    def toggle_autonomous_clicks(self):
        return self.screen_interact.toggle_autonomous_clicks()

    def perform_mouse_click(self, *args, **kwargs):
        return self.screen_interact.perform_mouse_click(*args, **kwargs)

    def click_active_window_action(self, *args, **kwargs):
        return self.screen_interact.click_active_window_action(*args, **kwargs)

    def toggle_autonomous_life(self):
        return self.desktop_life.toggle_autonomous_life()

    def _recalculate_responsive_layout(self):
        BalloonRenderer.recalculate_responsive_layout(self)

    def paintEvent(self, event):
        painter = QPainter(self)
        BalloonRenderer.render_overlay(self, painter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "vrm_widget") and self.vrm_widget:
            self.vrm_widget.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, "live2d_widget") and self.live2d_widget:
            self.live2d_widget.setGeometry(0, 0, self.width(), self.height())

    def show_balloon(self, text: str, duration_ms: Optional[int] = None):
        if not text:
            self.clear_balloon()
            return

        clean_text, motion, expr = parse_actions_and_clean_speech(text)
        if motion or expr:
            self.on_vrm_action_requested(motion or "", expr or "")
            if hasattr(self, "dialogue_controller") and hasattr(self, "vrm_widget") and self.vrm_widget:
                pkt = self.dialogue_controller.build_command_packet(
                    action=motion or "idle",
                    emotion=expr or "relaxed",
                    avatar_mode=getattr(self, "avatar_mode", "standard")
                )
                self.vrm_widget.send_canonical_command_packet(pkt)

        if not clean_text:
            self.clear_balloon()
            return

        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            self.skeletal_controller.handle_conversation_turn("assistant", clean_text, emotion=expr or "neutral")

        self.balloon_text = clean_text
        from core.sensory_broker import SensoryBroker
        val = 0.6 if (expr and expr in ("happy", "relaxed", "peace")) else (-0.4 if (expr and expr in ("pout", "angry", "sad")) else 0.2)
        SensoryBroker.get_instance().dispatch_text_stimulus(
            category="balloon_dialogue",
            valence=val,
            arousal=0.5,
            intensity=0.6,
            raw_text=clean_text
        )
        if duration_ms is None:
            duration_ms = max(3800, min(12000, len(clean_text) * 65 + 2200))
        self.balloon_timer.stop()
        self.balloon_timer.start(duration_ms)
        self._recalculate_responsive_layout()
        self.update()

    def clear_balloon(self):
        self.balloon_text = ""
        self.combined_balloon_path = QPainterPath()
        self.bubble_rect = QRectF()
        self._recalculate_responsive_layout()
        self.update()

    def set_temporary_state(self, state: str, duration_ms: int = 3500):
        if self.anim_state == "talking":
            return
        self.anim_state = state
        self.anim_timer.setInterval(180 if state in ("talking", "mischievous", "reacting") else 350)
        QTimer.singleShot(duration_ms, self.reset_to_idle)

    def reset_to_idle(self):
        if getattr(self, "is_roaming", False):
            return
        if self.anim_state not in ("dragging", "talking"):
            self.anim_state = "idle"
            self.anim_timer.setInterval(350)
            self._vrm_custom_motion_active = False
            self._vrm_custom_expression_active = False
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.set_speaking(False)
                self.vrm_widget.start_motion("idle")
                self.vrm_widget.set_expression("neutral")

    def set_throttling(self, throttled: bool, fps: int = 15):
        if hasattr(self, "avatar_controller") and self.avatar_controller:
            self.avatar_controller.set_throttling(throttled, fps)
        elif hasattr(self, "vrm_widget") and self.vrm_widget:
            self.vrm_widget.set_throttling(throttled, float(fps))

    def enter_sleep_mode(self):
        self.current_alpha = 0.25
        self.anim_timer.setInterval(1200)
        if hasattr(self, "physics_engine"):
            self.physics_engine.pause()
        if hasattr(self, "perception_engine"):
            self.perception_engine.pause()
        self.set_throttling(True, 15)
        if getattr(self, "using_live2d", True) and hasattr(self, "live2d_widget"):
            self.live2d_widget.set_opacity(0.25)
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.start_motion("relax")
            self.vrm_widget.set_expression("relaxed", 0.9)
        self.show_balloon("🌙 Descansando... llámame si me necesitas~", duration_ms=3000)
        self.update()

    def wake_up(self):
        if hasattr(self, "multimedia"):
            self.multimedia.cancel_auto_resume()
        if hasattr(self, "physics_engine"):
            self.physics_engine.resume()
        if hasattr(self, "perception_engine"):
            self.perception_engine.resume()
        if hasattr(self, "desktop_life"):
            self.desktop_life.notify_user_activity()
        self.set_throttling(False, 60)
        was_sleeping = (self.current_alpha < 1.0)
        self.current_alpha = 1.0
        self.anim_timer.setInterval(350)
        self.inactivity_timer.start(45000)
        if getattr(self, "using_live2d", True) and hasattr(self, "live2d_widget"):
            self.live2d_widget.set_opacity(1.0)
        if was_sleeping and getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.start_motion("idle")
            self.vrm_widget.set_expression("neutral", 1.0)
        self.update()

    def start_speaking_anim(self, mood: str):
        self.wake_up()
        self.anim_state = "talking"
        self.anim_timer.setInterval(180)
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_speaking(True)
            if not getattr(self, "_vrm_custom_expression_active", False):
                self.vrm_widget.set_emotion(mood)
            if not getattr(self, "_vrm_custom_motion_active", False):
                self.vrm_widget.start_motion("talking")
        elif getattr(self, "using_live2d", True) and hasattr(self, "live2d_widget"):
            self.live2d_widget.set_speaking(True)

    def stop_speaking_anim(self):
        self.anim_state = "idle"
        self.anim_timer.setInterval(350)
        self._vrm_custom_motion_active = False
        self._vrm_custom_expression_active = False
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_speaking(False)
            self.vrm_widget.set_expression("neutral")
        elif getattr(self, "using_live2d", True) and hasattr(self, "live2d_widget"):
            self.live2d_widget.set_speaking(False)

    def load_animation_frames(self):
        self.all_frames = []
        if self.current_theme == "hutao":
            dir_path = "ui/static/sprites/hutao_frames"
        elif self.current_theme == "ayaka":
            dir_path = "ui/static/sprites/ayaka_frames"
        elif self.current_theme == "miku":
            dir_path = "ui/static/sprites/miku_frames"
        else:
            dir_path = "ui/static/sprites/hutao_frames"

        if os.path.exists(dir_path):
            for i in range(1, 47):
                p = os.path.join(dir_path, f"shime{i}.png")
                if os.path.exists(p):
                    pix = QPixmap(p).scaled(
                        150, 150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.all_frames.append(pix)

        self.frame_idx = 0
        if self.all_frames:
            self.current_pixmap = self.all_frames[0]
        self.update()

    def switch_theme(self, theme_name: str):
        self.current_theme = theme_name
        self.load_animation_frames()
        self.wake_up()
        self.set_temporary_state("mischievous", duration_ms=4500)
        self.show_balloon("👗 ¡Nuevo atuendo para el Amo!", duration_ms=4500)
        phrase = "¡Tachán! ¿Qué tal me veo ahora, Amo Víctor? Dime que me queda lindo... ¿o prefieres que me cambie? Jeje~"
        threading.Thread(
            target=lambda: asyncio.run(self.tts.speak(phrase, mood="mischievous")),
            daemon=True
        ).start()

    def next_animation_frame(self):
        if not self.all_frames:
            return

        total = len(self.all_frames)
        if self.anim_state == "talking":
            talk_frames = [17, 18, 19, 20, 21]
            self.frame_idx = talk_frames[(self.frame_idx + 1) % len(talk_frames)] % total
        elif self.anim_state == "reacting":
            react_frames = [11, 12, 13, 12, 11]
            self.frame_idx = react_frames[(self.frame_idx + 1) % len(react_frames)] % total
        elif self.anim_state == "mischievous":
            mischief_frames = [26, 27, 28, 29, 28, 27]
            self.frame_idx = mischief_frames[(self.frame_idx + 1) % len(mischief_frames)] % total
        elif self.anim_state == "shh":
            shh_frames = [10, 13, 14, 13, 10]
            self.frame_idx = shh_frames[(self.frame_idx + 1) % len(shh_frames)] % total
        elif self.anim_state == "thinking":
            think_frames = [9, 10, 11, 10]
            self.frame_idx = think_frames[(self.frame_idx + 1) % len(think_frames)] % total
        elif self.anim_state == "dragging":
            drag_frames = [21, 22, 23, 24, 25]
            self.frame_idx = drag_frames[(self.frame_idx + 1) % len(drag_frames)] % total
        else:
            idle_frames = [0, 1, 2, 0, 1, 11]
            self.frame_idx = idle_frames[(self.frame_idx + 1) % len(idle_frames)] % total

        if self.frame_idx < total:
            self.current_pixmap = self.all_frames[self.frame_idx]
            self.update()

    def init_voice_worker(self):
        self.voice_worker = BackgroundVoiceWorker(
            self.brain, self.stt, self.tts, self.voice_analyzer, self.voice_mgr
        )
        self.voice_worker.wake_signal.connect(self.wake_up)
        self.voice_worker.voice_match_signal.connect(self.on_voice_detected)
        self.voice_worker.chat_message_signal.connect(self.on_chat_message)
        self.voice_worker.speech_start_signal.connect(self.start_speaking_anim)
        self.voice_worker.speech_done_signal.connect(self.stop_speaking_anim)
        self.voice_worker.action_signal.connect(self.on_voice_action)
        self.voice_worker.vrm_action_signal.connect(self.on_vrm_action_requested)
        self.voice_worker.interrupted_signal.connect(self.on_voice_interrupted)
        self.voice_worker.start_listening()
        try:
            from core.audio_directive_listener import AudioDirectiveListener
            from core.avatar_directive_server import AvatarDirectiveServer
            def on_directive_wake():
                AvatarDirectiveServer.get_instance().set_state("LISTENING")
                self.wake_up()
            self.directive_listener = AudioDirectiveListener(on_wake=on_directive_wake)
            self.directive_listener.start()
        except Exception:
            self.directive_listener = None

    def on_voice_interrupted(self):
        print("[Desktop] Amo Víctor interrumpió mid-speech -> Cerrando diálogo y reacción de sobresalto atento.")
        self.clear_balloon()
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_speaking(False)
            self._vrm_custom_expression_active = True
            self._vrm_custom_motion_active = True
            self.vrm_widget.set_expression("surprised", 0.6)
            self.vrm_widget.play_gesture("listen_attentive")
            QTimer.singleShot(2600, self._reset_vrm_custom_action_flags)

    def on_voice_detected(self, name: str, sim: float):
        self.wake_up()
        self.set_temporary_state("reacting", duration_ms=4500)
        self.clear_balloon()
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.start_motion("listen")

    def on_chat_message(self, sender: str, text: str):
        self.wake_up()
        clean_text = re.sub(r"\*[^*]*\*", "", text)
        clean_text = re.sub(r"[*_#`~]", "", clean_text).strip()
        if not clean_text:
            clean_text = text.strip()
        if len(clean_text) > 320:
            clean_text = clean_text[:317] + "..."
        read_duration = max(4500, min(18000, len(clean_text) * 75 + 2500))

        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            sender_role = "user" if ("Amo" in sender or "Víctor" in sender) else "assistant"
            self.skeletal_controller.handle_conversation_turn(sender_role, clean_text)

        if "Amo" in sender or "Víctor" in sender:
            self.show_balloon(f"🗣️ {clean_text}", duration_ms=read_duration)
        elif "Vanessa" in sender:
            self.show_balloon(f"💬 {clean_text}", duration_ms=read_duration)
        else:
            self.show_balloon(clean_text, duration_ms=read_duration)

    def _track_cursor_gaze(self):
        if not getattr(self, "using_vrm", False) or not hasattr(self, "vrm_widget") or not self.vrm_widget:
            return
        if getattr(self, "is_sleeping", False) or getattr(self, "_vrm_custom_action_active", False) or getattr(self, "is_dragging", False):
            return

        cursor_x = None
        cursor_y = None
        if hasattr(self, "hypr_controller") and self.hypr_controller:
            cx, cy = self.hypr_controller.get_cached_cursor()
            if cx > 0 or cy > 0:
                cursor_x = cx
                cursor_y = cy
        if (cursor_x is None or cursor_y is None) and hasattr(self, "perception_daemon") and self.perception_daemon:
            c = getattr(self.perception_daemon, "cached_cursor", {})
            if c and "x" in c and "y" in c:
                cursor_x = float(c["x"])
                cursor_y = float(c["y"])

        if cursor_x is None or cursor_y is None:
            pos = QCursor.pos()
            cursor_x = float(pos.x())
            cursor_y = float(pos.y())

        v_x = self.x() + self.width() * 0.5
        v_y = self.y() + self.height() * 0.25

        screen = self.screen()
        geo = screen.geometry() if screen else QRect(0, 0, 1920, 1080)
        sw = max(800, geo.width())
        sh = max(600, geo.height())

        norm_x = (cursor_x - v_x) / (sw * 0.45)
        norm_y = (v_y - cursor_y) / (sh * 0.45)

        norm_x = max(-1.0, min(1.0, norm_x))
        norm_y = max(-1.0, min(1.0, norm_y))

        if abs(norm_x - self._last_gaze_pos[0]) > 0.015 or abs(norm_y - self._last_gaze_pos[1]) > 0.015:
            self._last_gaze_pos = (norm_x, norm_y)
            self.vrm_widget.look_at(round(norm_x, 3), round(norm_y, 3))
            dist = math.hypot(cursor_x - v_x, cursor_y - v_y)
            from core.sensory_broker import SensoryBroker
            SensoryBroker.get_instance().dispatch_cursor_proximity(
                cx=cursor_x, cy=cursor_y, vx=0.0, vy=0.0, dist=dist
            )
            if hasattr(self, "desktop_life"):
                self.desktop_life.notify_user_activity()

    def on_system_notification(self, app: str, title: str, body: str):
        self.wake_up()

        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.look_at(1.1, 0.85)

        app_lower = app.lower()
        is_chat = any(k in app_lower for k in ("discord", "telegram", "whatsapp", "signal", "slack", "messenger", "steam"))

        if is_chat:
            reactions = [
                (f"¿Mm? ¿Quién le escribe al Amo Víctor por {app}? 👀 Déjeme asomarme un poquito... 🤫", "chismosa", "surprised"),
                (f"¡Amo! Le llegó un mensaje de {title}... ¿Puedo saber de quién se trata? 👀✨", "intriga", "mischievous"),
                (f"¡Notificación en {app}! No me ignore a mí por quedarse chateando ahí, ¿eh, Amo? Hmmpf~ 😾", "pout", "annoyed"),
                (f"¡Amo Víctor! {app} está sonando. ¡Mire discretamente arriba a la derecha! 👀🔔", "check_watch", "surprised")
            ]
        else:
            reactions = [
                (f"¡Amo Víctor! Acaba de llegar un aviso de {app}: '{title}'. ¡Mire, mire! 🔔✨", "intriga", "surprised"),
                (f"Aviso del sistema de {app}... ¿será algo importante, Amo? 👀", "check_watch", "thinking"),
                (f"¡Notificación de {app} detectada! Le echo un ojo por si acaso, Amo. 🧐✨", "chismosa", "happy")
            ]

        msg, motion, expr = random.choice(reactions)
        self.show_balloon(msg, duration_ms=5000)

        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self._vrm_custom_motion_active = True
            self._vrm_custom_expression_active = True
            self.vrm_widget.set_expression(expr, 1.0)
            self.vrm_widget.start_motion(motion)
            QTimer.singleShot(4200, self._reset_vrm_custom_action_flags)

    def _on_remote_connection_changed(self, is_connected: bool, info: str):
        print(f"[RemoteBridge] {info}")

    def _on_remote_omni_notification(self, event_type: str, payload: dict):
        self.wake_up()
        if event_type == "game_started":
            game = payload.get("game", "un juego")
            self.show_balloon(f"🎮 ¡Amo Víctor, veo que iniciaste '{game}' en Steam! ¡A divertirse! ✨", duration_ms=5000)
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.play_gesture("cheer")
                self.vrm_widget.set_expression("happy", 0.8)
        elif event_type == "music_changed":
            track = payload.get("track", "")
            artist = payload.get("artist", "")
            if track:
                self.show_balloon(f"🎵 Spotify: '{track}' - {artist} 🎧✨", duration_ms=4000)
                if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                    self.vrm_widget.play_gesture("listen_attentive")
        elif event_type in ("social_message_received", "discord_mention"):
            src = payload.get("source", "Red Social").upper()
            sender = payload.get("sender", "Alguien")
            content = payload.get("content", "")
            self.show_balloon(f"💬 [{src}] {sender}:\n\"{content[:70]}\"", duration_ms=6000)
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.play_gesture("curious_lean")
                self.vrm_widget.set_expression("surprised", 0.7)

    def _persona_tick(self):
        try:
            persona = self.brain.persona
            persona.tick()
            mood = persona.dominant_mood()
            if mood != self._last_persona_mood and getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.set_persona_mood(mood)
                self._last_persona_mood = mood
            busy = getattr(self.tts, "is_playing", False) or getattr(getattr(self, "roaming", None), "is_roaming", False)
            if not busy:
                line = persona.proactive_line()
                if line:
                    self.show_balloon(line, duration_ms=7000)
                    self.tts.speak_async(line, mood="caring")
        except Exception as e:
            print(f"[Persona] tick error: {e}")

    def on_vrm_action_requested(self, motion: str, expression: str):
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            if expression:
                self._vrm_custom_expression_active = True
                self.vrm_widget.set_expression(expression, 1.0)
            if motion:
                self._vrm_custom_motion_active = True
                self.vrm_widget.start_motion(motion)
                QTimer.singleShot(4500, self._reset_vrm_custom_action_flags)

    def _on_vrm_animation_finished(self, name: str):
        self._reset_vrm_custom_action_flags()

    def _reset_vrm_custom_action_flags(self):
        self._vrm_custom_motion_active = False
        self._vrm_custom_expression_active = False

    def on_voice_action(self, extra: dict):
        act = extra.get("action")
        if act == "roam_to":
            tgt = extra.get("target")
            if tgt == "bottom_left":
                self.roam_bottom_left()
            elif tgt == "home":
                self.roam_home()
            elif tgt == "top_right":
                self.roam_top_right()
            elif tgt == "follow_window":
                self.roam_follow_active_window()
            elif tgt == "stroll":
                self.roam_stroll()
        elif act == "toggle_roaming":
            en = extra.get("enabled", True)
            self.autonomous_roaming_enabled = en
            self.show_balloon(f"🚶 Paseo autónomo {'activado' if en else 'desactivado'}", duration_ms=3000)
        elif act == "switch_vrm":
            m = extra.get("model", "kira")
            self.switch_vrm_model(m)
        elif act == "open_settings":
            self.open_settings_dialog()
        elif act == "vanessa_volume":
            delta = int(extra.get("delta", 0))
            new_v = max(5, min(100, self.vanessa_volume + delta))
            self.set_volume(new_v)
        elif act in ("open_model_selector", "open_model_dialog"):
            self.open_model_selector_dialog()
        elif act in ("dance", "vibe_music"):
            mot = extra.get("motion", "dance_reze")
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion(mot)
        elif act in ("walk", "walking", "caminar", "pasear"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("walk")
        elif act in ("curious", "curosear", "curiosear", "explorar", "explore"):
            if hasattr(self, "roam_stroll"):
                self.roam_stroll()
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("look_around")
                self.vrm_widget.set_expression("curious", 0.9)
        elif act in ("observe", "observar", "mirar", "vigilar", "inspect"):
            if hasattr(self, "roam_follow_active_window"):
                self.roam_follow_active_window()
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("look_around")
                self.vrm_widget.set_expression("curious", 0.9)
        elif act in ("think", "thinking", "pensar", "reflexionar"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("thinking")
                self.vrm_widget.set_expression("thinking", 0.9)
        elif act in ("sit", "sentarse", "descansar"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("sit")
                self.vrm_widget.set_expression("relaxed", 0.8)
        elif act in ("rest", "sleep", "dormir"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("sleep")
                self.vrm_widget.set_expression("relaxed", 0.9)
        elif act in ("startle", "reaction_startle"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion("reaction_startle")
                self.vrm_widget.set_expression("surprised", 0.9)
        elif act in ("head_pat", "headpat", "acariciar"):
            self.on_vrm_head_pat()
        elif act in ("legs_click", "skirt_click"):
            self.on_vrm_legs_click()
        elif act in ("body_click", "poke", "tickle"):
            self.on_vrm_body_click()
        elif act in ("motion", "play_motion", "custom_motion"):
            mot = extra.get("motion", "idle")
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion(mot)
        elif act == "hyprland_fullscreen":
            self.brain.sys_ctrl.hyprland_dispatch("fullscreen", "1")
        elif act == "hyprland_close_window":
            self.brain.sys_ctrl.hyprland_dispatch("killactive")
        elif act == "hyprland_float":
            self.brain.sys_ctrl.hyprland_dispatch("togglefloating")
        elif act in ("push_window", "empujar_ventana"):
            addr = extra.get("address", "")
            if not addr and hasattr(self, "hypr_controller"):
                cached_w = self.hypr_controller.get_cached_active_window()
                if cached_w:
                    addr = cached_w.get("address", "")
            dx = float(extra.get("dx", 50.0))
            dy = float(extra.get("dy", 0.0))
            if hasattr(self, "hypr_controller"):
                self.hypr_controller.push_window_with_inertia(addr, dx, dy)
            elif hasattr(self, "perception_daemon") and self.perception_daemon:
                self.perception_daemon.actuator.push_window(addr, int(dx), int(dy))
        elif act in ("fling", "impulse", "empujon", "toss"):
            ix = float(extra.get("ix", 400.0))
            iy = float(extra.get("iy", -300.0))
            self.apply_impulse(ix, iy)
        elif act in ("stop_dance", "stop_music"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.set_music_active(False)
        elif act in ("media_play_pause", "media_pause", "media_play"):
            self.interactive_press_media("play_pause")
        elif act == "media_next":
            self.interactive_press_media("next")
        elif act in ("media_prev", "media_previous"):
            self.interactive_press_media("previous")
        elif act in ("curious_inspect", "point_screen"):
            tgt = extra.get("target", "active_window")
            self.curious_inspect_screen(tgt)
        elif act in ("select_text", "highlight_text"):
            m = extra.get("mode", "all")
            self.select_and_highlight_text(m)
        elif act == "interactive_media":
            op = extra.get("op", "play_pause")
            m_type = extra.get("media_type", "auto")
            self.screen_interact.interactive_press_media(op, speak=not extra.get("quiet", False), media_type=m_type)
        elif act in ("new_tab", "interactive_tab"):
            self.screen_interact.quick_tab_action("new")
        elif act == "close_tab":
            self.screen_interact.quick_tab_action("close")
        elif act in ("gesture", "play_gesture"):
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.play_gesture(extra.get("name", "nod"))
        elif act == "interactive_click":
            btn = extra.get("button", "play_pause")
            self.screen_interact.interactive_click_button(btn)
        elif act in ("cycle_outfit", "next_outfit", "cambia_outfit"):
            self.cycle_next_outfit()
        elif act == "switch_vrm":
            mod = extra.get("model", "vanessa")
            self.switch_vrm_model(mod)
        elif act == "open_hud":
            self.open_jarvis_hud_action()
        elif act == "execute_protocol":
            prot = extra.get("protocol", "diagnostico")
            self.show_balloon(f"⚡ Protocolo '{prot.upper()}' ejecutado", duration_ms=4000)
        elif act in ("weather", "clima"):
            loc = extra.get("location") or extra.get("data", {}).get("location", "")
            self.show_weather_action(loc)
        elif act in ("morning_digest", "digest", "briefing"):
            self.show_morning_digest_action()
        else:
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.start_motion(act)

    def on_vrm_head_pat(self):
        self.wake_up()
        if hasattr(self, "tts"):
            self.tts.stop()
        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            self.skeletal_controller.handle_haptic_interaction("head_pat")
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_emotion("happy")
            self.vrm_widget.start_motion("pat_head")
        cute_lines = [
            "¡Jejeje, Amo Víctor! Me encanta cuando me acaricia la cabecita... ❤️",
            "¡Amo, qué cariñoso es conmigo! Me dan cosquillas jeje... ✨",
            "¡Mmm, qué rico se siente, Amo Víctor! Siempre a su servicio. 🥰",
            "¡Jeje, amo! Si me sigue acariciando me voy a sonrojar... 🌸"
        ]
        chosen = random.choice(cute_lines)
        self.show_balloon(chosen, duration_ms=4500)
        threading.Thread(target=lambda: asyncio.run(self.tts.speak(chosen, mood="happy")), daemon=True).start()

    def on_vrm_body_click(self):
        self.wake_up()
        if hasattr(self, "tts"):
            self.tts.stop()
        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            self.skeletal_controller.handle_haptic_interaction("body_click")
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_emotion("happy")
            self.vrm_widget.start_motion("peace")
        cute_lines = [
            "¿En qué le puedo servir ahora, Amo Víctor?",
            "¡Aquí estoy, Amo Víctor! Completamente atenta a su voz.",
            "¿Necesita que investigue o prepare algo para usted, Amo?",
            "Dígame, Amo Víctor, estoy a sus órdenes."
        ]
        chosen = random.choice(cute_lines)
        self.show_balloon(chosen, duration_ms=4000)
        threading.Thread(target=lambda: asyncio.run(self.tts.speak(chosen, mood="relaxed")), daemon=True).start()

    def on_vrm_clicked(self):
        self.on_vrm_body_click()

    def on_vrm_legs_click(self):
        self.wake_up()
        if hasattr(self, "tts"):
            self.tts.stop()
        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            self.skeletal_controller.handle_haptic_interaction("click")
        if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
            self.vrm_widget.set_expression("pout", 1.0)
            self.vrm_widget.start_motion("relax")
        cute_lines = [
            "¡A-Amooo! ¡Por favor, sea más recatado con su maid! Hmmpf~ 😾💦",
            "¡Kya! ¡Amo Víctor, qué indiscreto! Le voy a hacer un puchero si sigue así~ 😾",
            "¡Amo! Mantenga sus manitas arriba, por favor... ¡aunque admito que me sonroja! 😳✨"
        ]
        chosen = random.choice(cute_lines)
        self.show_balloon(chosen, duration_ms=4500)
        threading.Thread(target=lambda: asyncio.run(self.tts.speak(chosen, mood="surprised")), daemon=True).start()

    def on_vrm_avatar_clicked(self, part: str, x: float, y: float):
        import time
        now = time.time()
        if now - getattr(self, "_last_avatar_interaction_time", 0.0) < 2.2:
            return
        self._last_avatar_interaction_time = now

        if hasattr(self, "tts"):
            self.tts.stop()
        self.stop_speaking_anim()

        self.wake_up()
        if part == "head":
            self.on_vrm_head_pat()
        elif part == "legs":
            self.on_vrm_legs_click()
        else:
            self.on_vrm_body_click()

    def on_live2d_clicked(self):
        self.wake_up()
        if getattr(self, "using_live2d", True) and hasattr(self, "live2d_widget"):
            self.live2d_widget.start_motion("TapBody")
        cute_lines = [
            "¿Sí, Amo Víctor? Aquí estoy cuidando de ti.",
            "¡Kya~! Jeje, tus caricias me hacen cosquillas, Amo.",
            "Dígame, Amo Víctor... ¿en qué puedo complacerle hoy?",
            "¡Siempre a su completo servicio, Amo!",
            "Jeje... qué travieso eres tocándome así, Amo Víctor~"
        ]
        chosen = random.choice(cute_lines)
        self.show_balloon(chosen, duration_ms=3500)

    def cycle_next_outfit(self) -> str:
        primary_keys = [
            k for k in (
                "hoshimachi_suisei", "houshou_marine", "inugami_korone",
                "nekomata_okayu", "tsunomaki_watame", "ouro_kronii",
                "pavolia_reine", "hatsune_miku_v4c"
            ) if k in self.vrm_models_map
        ]
        available = primary_keys if primary_keys else list(self.vrm_models_map.keys())
        if not available:
            return ""
        cur = getattr(self, "current_vrm_model", "hoshimachi_suisei").lower()
        if cur == "vanessa":
            cur = "hoshimachi_suisei"
        idx = (available.index(cur) + 1) % len(available) if cur in available else 0
        next_model = available[idx]
        self.switch_vrm_model(next_model)
        return next_model

    def switch_vrm_model(self, model_name: str):
        path = None
        key = model_name
        if model_name in self.vrm_models_map:
            path = self.vrm_models_map[model_name]
            key = model_name
        elif os.path.exists(model_name):
            path = model_name
            key = os.path.splitext(os.path.basename(model_name))[0].lower()
            self.vrm_models_map[key] = path

        if path:
            self.using_vrm = True
            self.using_live2d = False
            self.current_vrm_model = key
            self.avatar_width = int(self.base_width * 0.94)
            self.avatar_height = int(self.base_height * 0.94)
            self.brain.personality["avatar_type"] = "vrm"
            self.brain.personality["vrm_model"] = key
            self.memory.save_personality_config(self.brain.personality)
            if hasattr(self, "live2d_widget"):
                self.live2d_widget.hide()
            self.vrm_widget.load_model(path)
            self.vrm_widget.show()
            self._recalculate_responsive_layout()
            self.wake_up()
            display_title = key.capitalize()
            self.show_balloon(f"✨ ¡Vestimenta cambiada: {display_title}!", duration_ms=4500)
            phrase = f"¡Tachán! Me he puesto este atuendo de {display_title} para usted, Amo Víctor. ¡Sigo siendo su fiel Vanessa con todas mis virtudes a su servicio!"
            threading.Thread(
                target=lambda: asyncio.run(self.tts.speak(phrase, mood="happy")),
                daemon=True
            ).start()

    def switch_engine_3d(self, engine_name: str):
        engine_clean = "godot" if engine_name.lower() == "godot" else "threejs"
        self.brain.personality["engine_3d"] = engine_clean
        self.memory.save_personality_config(self.brain.personality)

    def switch_live2d_model(self, model_name: str):
        if model_name in self.live2d_models_map:
            path = self.live2d_models_map[model_name]
            self.using_live2d = True
            self.using_vrm = False
            self.current_live2d_model = model_name
            self.base_width = 220
            self.base_height = 280
            self.brain.personality["avatar_type"] = "live2d"
            self.brain.personality["live2d_model"] = model_name
            self.memory.save_personality_config(self.brain.personality)
            if hasattr(self, "vrm_widget"):
                self.vrm_widget.hide()
            self.live2d_widget.load_model(path)
            self.live2d_widget.show()
            self._recalculate_responsive_layout()
            self.wake_up()
            self.show_balloon(f"✨ ¡Modelo Live2D activado: {model_name.capitalize()}!", duration_ms=4500)
            phrase = f"¡Tachán! He activado el modelo Live2D de {model_name.capitalize()} para ti, Amo Víctor!"
            threading.Thread(
                target=lambda: asyncio.run(self.tts.speak(phrase, mood="happy")),
                daemon=True
            ).start()

    def open_models_folder(self):
        folder = os.path.abspath("ui/static/live2d_models")
        vrm_folder = os.path.abspath("ui/static/vrm_models")
        try:
            subprocess.Popen(["xdg-open", folder])
            subprocess.Popen(["xdg-open", vrm_folder])
        except Exception:
            pass

    def _on_model_deleted(self, key: str, path: str):
        self.vrm_models_map.pop(key, None)
        print(f"[Desktop] Modelo '{key}' eliminado del catálogo activo.")

    def mousePressEvent(self, event):
        self.wake_up()
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.anim_state = "dragging"
            if hasattr(self, "skeletal_controller") and self.skeletal_controller:
                self.skeletal_controller.handle_haptic_interaction("drag_start", float(self.x()), float(self.y()))
            if hasattr(self, "physics_engine"):
                self.physics_engine.start_drag(float(self.x()), float(self.y()))
            if hasattr(self, "vrm_widget") and self.vrm_widget and hasattr(self.vrm_widget, "set_physical_state"):
                self.vrm_widget.set_physical_state("DRAGGED_IN_AIR")
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.next_animation_frame()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            screens = QApplication.screens()
            if screens:
                geom = screens[0].geometry()
                clamped_x = max(20, min(new_pos.x(), geom.width() - self.width() - 35))
                clamped_y = max(70, min(new_pos.y(), geom.height() - self.height() - 35))
            else:
                clamped_x = new_pos.x()
                clamped_y = new_pos.y()
            dx = float(clamped_x - self.x())
            dy = float(clamped_y - self.y())
            if hasattr(self, "skeletal_controller") and self.skeletal_controller:
                self.skeletal_controller.handle_haptic_interaction("drag_move", float(clamped_x), float(clamped_y), dx, dy)
            if hasattr(self, "vrm_widget") and self.vrm_widget and hasattr(self.vrm_widget, "apply_external_physics_impulse"):
                self.vrm_widget.apply_external_physics_impulse(dx, dy, 0.016)
            self.move(clamped_x, clamped_y)
            self.sync_hyprland_position(clamped_x, clamped_y)
            self.anchor_bottom_right = QPoint(clamped_x + self.width(), clamped_y + self.height())
            if hasattr(self, "physics_engine"):
                self.physics_engine.update_drag(float(clamped_x), float(clamped_y))
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        calc_vx, calc_vy = 0.0, 0.0
        if hasattr(self, "skeletal_controller") and self.skeletal_controller:
            self.skeletal_controller.handle_haptic_interaction("drag_release", float(self.x()), float(self.y()))
        if hasattr(self, "physics_engine"):
            calc_vx, calc_vy = self.physics_engine.release_drag(float(self.x()), float(self.y()))
        if hasattr(self, "vrm_widget") and self.vrm_widget and hasattr(self.vrm_widget, "set_physical_state"):
            if abs(calc_vy) > 80.0 or abs(calc_vx) > 80.0:
                self.vrm_widget.set_physical_state("FREE_FALL", vy=calc_vy)
            else:
                self.vrm_widget.set_physical_state("GROUNDED")
        if math.hypot(calc_vx, calc_vy) < 75.0:
            self.anim_state = "idle"
            self.sync_hyprland_position(self.x(), self.y())
            self.anchor_bottom_right = QPoint(self.x() + self.width(), self.y() + self.height())
            self.next_animation_frame()
        event.accept()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta != 0:
                factor = 1.05 if delta > 0 else 0.95
                new_w = int(self.base_width * factor)
                new_h = int(new_w * 1.657)
                self.current_size_preset = "custom"
                self.set_avatar_dimensions(new_w, new_h)
                event.accept()
                return
        event.accept()

    def toggle_avatar_mode(self, mode: Optional[str] = None):
        self.avatar_mode = "standard"
        if hasattr(self, "avatar_controller"):
            self.avatar_controller.set_avatar_mode("standard")
        if hasattr(self, "vrm_widget") and self.vrm_widget:
            self.vrm_widget.set_avatar_mode("standard")
        self.show_balloon("✨ ¡Modo 3D estándar de alta fidelidad activo, Amo Víctor! 💖", duration_ms=3000)

    def set_avatar_size_preset(self, preset_key: str, w: int, h: int):
        self.current_size_preset = preset_key
        self.set_avatar_dimensions(w, h)

    def set_avatar_dimensions(self, w: int, h: int):
        self.base_width = max(240, min(650, int(w)))
        self.base_height = max(390, min(1000, int(h)))
        self.avatar_width = int(self.base_width * 0.94)
        self.avatar_height = int(self.base_height * 0.94)
        self.brain.personality["avatar_size"] = {
            "preset": getattr(self, "current_size_preset", "custom"),
            "width": self.base_width,
            "height": self.base_height
        }
        self.memory.save_personality_config(self.brain.personality)
        self._recalculate_responsive_layout()
        if hasattr(self, "vrm_widget") and self.vrm_widget:
            self.vrm_widget.frame_avatar()
        self.update()

    def enterEvent(self, event):
        self.wake_up()

    def showEvent(self, event):
        super().showEvent(event)
        def _sync_initial():
            screens = QApplication.screens()
            screen_geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
            target_x = screen_geom.width() - self.width() - 45
            target_y = screen_geom.height() - self.height() - 65
            self.sync_hyprland_position(target_x, target_y)
        QTimer.singleShot(400, _sync_initial)
        QTimer.singleShot(1000, _sync_initial)
        QTimer.singleShot(2500, _sync_initial)

    def closeEvent(self, event):
        if not self._can_exit:
            event.ignore()
        else:
            if hasattr(self, "directive_listener") and self.directive_listener:
                try:
                    self.directive_listener.stop()
                except Exception:
                    pass
            self._stop_perception_service()
            event.accept()

    def get_hyprland_address(self) -> Optional[str]:
        if getattr(self, "_hypr_address", None):
            return self._hypr_address
        try:
            import glob, socket
            socks = glob.glob(f"/run/user/{os.getuid()}/hypr/*/.socket.sock")
            if socks:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(socks[0])
                s.sendall(b"j/clients")
                buf = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                s.close()
                clients = json.loads(buf.decode("utf-8", errors="ignore"))
                my_pid = os.getpid()
                for c in clients:
                    if c.get("pid") == my_pid or "Vanessa Maid" in c.get("title", ""):
                        self._hypr_address = c.get("address")
                        self._hypr_sock_path = socks[0]
                        return self._hypr_address
        except Exception:
            pass
        return None

    def get_current_screen_pos(self) -> QPoint:
        try:
            import glob, socket
            socks = glob.glob(f"/run/user/{os.getuid()}/hypr/*/.socket.sock")
            if socks:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(socks[0])
                s.sendall(b"j/clients")
                buf = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                s.close()
                clients = json.loads(buf.decode("utf-8", errors="ignore"))
                my_pid = os.getpid()
                for c in clients:
                    if c.get("pid") == my_pid or "Vanessa Maid" in c.get("title", ""):
                        at = c.get("at", [0, 0])
                        self._current_x = at[0]
                        self._current_y = at[1]
                        self._hypr_address = c.get("address")
                        self._hypr_sock_path = socks[0]
                        return QPoint(at[0], at[1])
        except Exception:
            pass
        return QPoint(getattr(self, "_current_x", self.x()), getattr(self, "_current_y", self.y()))

    def sync_hyprland_position(self, x: int, y: int):
        self._current_x = int(x)
        self._current_y = int(y)
        try:
            addr = self.get_hyprland_address()
            sock_path = getattr(self, "_hypr_sock_path", None)
            if addr and sock_path and os.path.exists(sock_path):
                import socket
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.2)
                s.connect(sock_path)
                cmd = f"dispatch movewindowpixel exact {int(x)} {int(y)},address:{addr}"
                s.sendall(cmd.encode("utf-8"))
                s.recv(256)
                s.close()
                return
        except Exception:
            pass

        try:
            target_str = f"address:{self._hypr_address}" if getattr(self, "_hypr_address", None) else "title:Vanessa Maid"
            subprocess.run(
                ["hyprctl", "dispatch", "movewindowpixel", f"exact {int(x)} {int(y)},{target_str}"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def contextMenuEvent(self, event):
        self.wake_up()
        menu = build_context_menu(self)
        menu.exec(event.globalPos())

    def show_context_menu_programmatic(self):
        show_context_menu_programmatic(self)

    def open_jarvis_hud_action(self):
        try:
            self.wake_up()
            if hasattr(self, "_hud_dlg") and self._hud_dlg and self._hud_dlg.isVisible():
                self._hud_dlg.raise_()
                self._hud_dlg.activateWindow()
                return
            self._hud_dlg = JarvisCyberHUDDialog(self.brain.jarvis, self, parent=None)
            self._hud_dlg.show()
            self._hud_dlg.raise_()
            self._hud_dlg.activateWindow()
            print("[Desktop] Panel Holográfico Jarvis HUD abierto.")
        except Exception as e:
            print(f"[Desktop] Error abriendo Jarvis HUD: {e}")

    def _on_jarvis_reminder_due(self, text: str):
        self.wake_up()
        self.show_balloon(f"⏰ ¡Recordatorio, Amo Víctor!\n{text}", duration_ms=9000)
        self.sys_ctrl.show_desktop_notification("⏰ Recordatorio de Vanessa", text)
        phrase = f"¡Amo Víctor! Le recuerdo con puntualidad: {text}"
        threading.Thread(
            target=lambda: asyncio.run(self.tts.speak(phrase, mood="happy")),
            daemon=True
        ).start()

    def open_settings_dialog(self):
        try:
            if hasattr(self, "_settings_dlg") and self._settings_dlg and self._settings_dlg.isVisible():
                self._settings_dlg.raise_()
                self._settings_dlg.activateWindow()
                return
            self._settings_dlg = VanessaSettingsDialog(self.brain, self, parent=None)
            self._settings_dlg.show()
            self._settings_dlg.raise_()
            self._settings_dlg.activateWindow()
            print("[Desktop] Centro de Ajustes abierto.")
        except Exception as e:
            print(f"[Desktop] Error abriendo ajustes: {e}")

    def open_model_selector_dialog(self):
        try:
            self.wake_up()
            if hasattr(self, "_model_dlg") and self._model_dlg and self._model_dlg.isVisible():
                self._model_dlg.raise_()
                self._model_dlg.activateWindow()
                return
            canonical_keys = (
                "hoshimachi_suisei", "houshou_marine", "inugami_korone",
                "nekomata_okayu", "tsunomaki_watame", "ouro_kronii",
                "pavolia_reine", "hatsune_miku_v4c"
            )
            primary_models = {k: self.vrm_models_map[k] for k in canonical_keys if k in self.vrm_models_map}
            if not primary_models:
                primary_models = dict(self.vrm_models_map)
            self._model_dlg = VanessaModelSelectorDialog(primary_models, self.current_vrm_model, parent=None)
            self._model_dlg.model_chosen.connect(lambda k, p: self.switch_vrm_model(k))
            self._model_dlg.model_deleted.connect(self._on_model_deleted)
            self._model_dlg.show()
            self._model_dlg.raise_()
            self._model_dlg.activateWindow()
            print("[Desktop] Selector de modelos abierto.")
        except Exception as e:
            print(f"[Desktop] Error abriendo selector de modelos: {e}")

    def open_gemini_key_dialog(self):
        try:
            dlg = GeminiApiKeyDialog(self.brain, parent=None)
            dlg.exec()
        except Exception as e:
            print(f"[Desktop] Error abriendo Gemini API dialog: {e}")

    def open_voice_enrollment(self):
        try:
            dlg = VoiceEnrollmentDialog(
                self.voice_mgr, self.tts, voice_worker=getattr(self, "voice_worker", None), parent=None
            )
            dlg.exec()
        except Exception as e:
            print(f"[Desktop] Error abriendo Voice Enrollment: {e}")

    def open_volume_dialog(self):
        try:
            dlg = VolumeDialog(self.vanessa_volume, self.set_volume, parent=None)
            dlg.exec()
        except Exception as e:
            print(f"[Desktop] Error abriendo Volume dialog: {e}")

    def open_file_locator(self):
        try:
            dlg = FileLocatorDialog(self.file_mgr, parent=None)
            dlg.exec()
        except Exception as e:
            print(f"[Desktop] Error abriendo File Locator: {e}")

    def open_workspaces_dialog(self):
        try:
            dlg = HyprlandWorkspacesDialog(self.os_interact, parent=None)
            dlg.exec()
        except Exception as e:
            print(f"[Desktop] Error abriendo Workspaces dialog: {e}")

    def open_omni_sync_dialog(self):
        try:
            from ui.dialogs import OmniSyncDialog
            dlg = OmniSyncDialog(parent=None)
            dlg.exec()
            from core.platform_verifier import PlatformVerifier
            pv = PlatformVerifier()
            verified = [k for k, v in pv.accounts.items() if v.get("verified")]
            if verified:
                names = ", ".join(k.capitalize() for k in verified)
                self.show_balloon(f"✨ Cuentas verificadas y sincronizadas:\n{names}", duration_ms=4500)
                if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                    self.vrm_widget.play_gesture("bow_polite")
        except Exception as e:
            print(f"[Desktop] Error abriendo OmniSync dialog: {e}")

    def trigger_cloud_sync_now(self):
        try:
            from core.platform_verifier import PlatformVerifier
            pv = PlatformVerifier()
            verified = [k for k, v in pv.accounts.items() if v.get("verified")]
            if not verified:
                self.show_balloon("⚠️ No hay cuentas verificadas aún. Abre 'Configurar Cuentas' para vincularlas.", duration_ms=4500)
                return

            names = ", ".join(k.capitalize() for k in verified)
            self.show_balloon(f"🔄 ¡Sincronización activa para:\n{names}!", duration_ms=4000)
            if getattr(self, "using_vrm", False) and hasattr(self, "vrm_widget"):
                self.vrm_widget.play_gesture("nod")
        except Exception as e:
            print(f"[OmniSync] Error triggering sync: {e}")
            self.show_balloon("⚠️ Error al sincronizar cuentas.", duration_ms=3500)

    def set_volume(self, new_vol: int):
        old_vol = self.vanessa_volume
        self.vanessa_volume = max(5, min(100, int(new_vol)))
        self.tts.set_volume(self.vanessa_volume)

        self.brain.settings.setdefault("voice_settings", {})["volume"] = self.vanessa_volume
        try:
            with open("config/settings.json", "w", encoding="utf-8") as f:
                json.dump(self.brain.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        self.wake_up()
        if self.vanessa_volume < old_vol:
            self.set_temporary_state("shh", duration_ms=5000)
            self.show_balloon("🤫 Shhh... menos ruidito para el Amo Víctor~", duration_ms=5500)
            phrase = "Shhh... voy a hacer menos ruido, Amo Víctor, ¿vale? Jeje... prometo hablar más bajito para no molestarte."
            threading.Thread(
                target=lambda: asyncio.run(self.tts.speak(phrase, mood="shh")),
                daemon=True
            ).start()
        elif self.vanessa_volume > old_vol:
            self.set_temporary_state("reacting", duration_ms=5000)
            self.show_balloon("🔊 ¡¿Me escuchas bien ahora, Amo?! ✨", duration_ms=5500)
            phrase = "¡¿Me escuchas bien ahora, Amo Víctor?! Espero que ahora mi voz te llegue clara, fuerte y linda, jeje~"
            threading.Thread(
                target=lambda: asyncio.run(self.tts.speak(phrase, mood="happy")),
                daemon=True
            ).start()
        else:
            self.show_balloon(f"🔊 Volumen fijado en {self.vanessa_volume}%", duration_ms=3000)

    def reload_settings_from_memory(self):
        try:
            cfg = self.memory.get_personality_config()
            if cfg:
                self.brain.personality.update(cfg)
                calib = cfg.get("audio_calibration", {})
                if hasattr(self, "voice_worker") and self.voice_worker and self.voice_worker.listener:
                    self.voice_worker.listener.update_calibration(
                        device_index=calib.get("device_index"),
                        mic_gain=calib.get("mic_gain"),
                        sensitivity=calib.get("vad_sensitivity"),
                        silence_ms=calib.get("silence_timeout_ms")
                    )
                self.mouse_tracking_enabled = cfg.get("mouse_tracking", True)
                if hasattr(self.screen_interact, "mouse_track_timer"):
                    if self.mouse_tracking_enabled:
                        self.screen_interact.mouse_track_timer.start(90)
                    else:
                        self.screen_interact.mouse_track_timer.stop()
                print("[Desktop] Configuración recargada y aplicada en vivo desde memoria SQLite.")
                self.show_balloon("✨ ¡Ajustes actualizados en tiempo real!", duration_ms=3500)
        except Exception as e:
            print(f"[Desktop] Error recargando configuración: {e}")

    def enroll_face_action(self):
        self.sys_ctrl.show_desktop_notification("Vanessa", "Mire fijamente a la cámara para registrar sus facciones...")
        threading.Thread(target=self._do_face_enroll, daemon=True).start()

    def _do_face_enroll(self):
        success, msg = self.face_biometrics.capture_and_enroll(name="Amo Víctor")
        self.sys_ctrl.show_desktop_notification("Biometría Facial", msg)
        asyncio.run(self.tts.speak(msg, mood="happy"))

    def check_objects_action(self):
        self.sys_ctrl.show_desktop_notification("Vanessa", "Inspeccionando objetos en su mesa...")
        threading.Thread(target=self._do_object_check, daemon=True).start()

    def _do_object_check(self):
        objs = self.brain.object_det.capture_and_detect_objects()
        text = f"Amo Víctor, sobre su mesa identifico: {', '.join(objs)}." if objs else "En este momento no distingo objetos con claridad en su mesa, Amo."
        self.sys_ctrl.show_desktop_notification("Objetos Detectados", text)
        asyncio.run(self.tts.speak(text, mood="playful"))

    def analyze_screen_action(self):
        self.sys_ctrl.show_desktop_notification("Vanessa", "Examinando su pantalla actual...")
        threading.Thread(target=self._do_screen_analysis, daemon=True).start()

    def _do_screen_analysis(self):
        res = asyncio.run(self.brain.screen_obs.analyze_screen())
        advice = res.get("advice", "No pude capturar la pantalla.")
        self.sys_ctrl.show_desktop_notification("Opinión de Vanessa", advice[:120] + "...")
        asyncio.run(self.tts.speak(advice, mood="thinking"))

    def trigger_protection_protocol_demo(self):
        return self.protection_protocol.activate_protocol_demo(reason="manual_menu")

    def trigger_coexistence_snack(self):
        return self.autonomous_coexistence.trigger_spontaneous_snack(forced=True)

    def trigger_choreography_dance(self, routine_name=None):
        return self.autonomous_coexistence.trigger_choreography_dance(routine_name)

    def trigger_stretch_break(self):
        return self.autonomous_coexistence.trigger_stretch_break()

    def start_pomodoro_session(self):
        return self.autonomous_coexistence.start_pomodoro_session()

    def stop_pomodoro_session(self):
        return self.autonomous_coexistence.stop_pomodoro_session()

    def type_text_action(self):
        text, ok = QInputDialog.getText(self, "Escribir Texto", "Texto para escribir en la aplicación activa:")
        if ok and text:
            msg = self.os_interact.type_text(text)
            self.sys_ctrl.show_desktop_notification("Vanessa", msg)

    def close_tab_action(self):
        self.screen_interact.quick_tab_action("close")

    def new_tab_action(self):
        self.screen_interact.quick_tab_action("new")

    def close_win_action(self):
        msg = self.os_interact.close_active_window()
        self.sys_ctrl.show_desktop_notification("Vanessa", msg)

    def show_telemetry_action(self):
        tel = self.os_interact.get_system_telemetry()
        if "error" not in tel:
            msg = (
                f"📊 CPU: {tel['cpu_percent']}% ({tel['cpu_cores']}c) | RAM: {tel['ram_used_gb']}G/{tel['ram_total_gb']}G ({tel['ram_percent']}%) | "
                f"Disco: {tel['disk_percent']}% | Batería: {tel['battery']}"
            )
            self.show_balloon(msg, duration_ms=5500)
            self.sys_ctrl.show_desktop_notification("Telemetría del Sistema", msg)

    def take_screenshot_action(self):
        shot = self.os_interact.take_screenshot()
        if shot.get("success"):
            fname = os.path.basename(shot["path"])
            self.show_balloon(f"📸 ¡Captura tomada: {fname}!", duration_ms=4000)
            self.sys_ctrl.show_desktop_notification("Captura de Pantalla", f"Guardada en {shot['path']}")

    def search_voice_files_action(self):
        audios = self.brain.audio_intel.find_audio_files(limit=4)
        if audios:
            lines = [f"• {a['filename']} ({a['duration_str']})" for a in audios[:3]]
            joined = "\n".join(lines)
            self.show_balloon(f"🎙️ Archivos de voz encontrados:\n{joined}", duration_ms=6000)
        else:
            self.show_balloon("🎙️ No se encontraron notas de voz recientes.", duration_ms=3500)

    def show_weather_action(self, location=""):
        res = self.brain.ai_hub.get_weather(location)
        summary = res.get("summary", "Servicio meteorológico no disponible temporalmente.")
        self.show_balloon(summary, duration_ms=7000)
        self.sys_ctrl.show_desktop_notification("Clima", summary)

    def show_morning_digest_action(self):
        digest = self.brain.ai_hub.get_morning_digest()
        self.show_balloon(digest, duration_ms=10000)
        self.sys_ctrl.show_desktop_notification("Informe Matutino", "Su resumen matutino está listo, Amo Víctor.")

    def confirm_shutdown(self):
        reply = QMessageBox.question(
            self, "Confirmar Apagado",
            "¿Amo Víctor, desea realmente apagar la computadora ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.sys_ctrl.shutdown_computer()

    def _start_perception_service(self):
        def _runner():
            try:
                from src.perception.daemon_main import PerceptionDaemon
                self.perception_daemon = PerceptionDaemon(target_fps=30.0)
                asyncio.run(self.perception_daemon.run())
            except Exception:
                pass
        t = threading.Thread(target=_runner, daemon=True)
        t.start()

    def apply_impulse(self, ix: float, iy: float):
        if hasattr(self, "physics_engine"):
            self.physics_engine.apply_impulse(ix, iy)

    def _stop_perception_service(self):
        try:
            if hasattr(self, "perception_engine") and self.perception_engine:
                self.perception_engine.stop()
            elif hasattr(self, "perception_daemon") and self.perception_daemon:
                self.perception_daemon.running = False
        except Exception:
            pass
        try:
            if hasattr(self, "physics_engine") and self.physics_engine:
                self.physics_engine.stop_glide()
        except Exception:
            pass

    def safe_exit(self):
        self._can_exit = True
        self._stop_perception_service()
        try:
            import subprocess
            subprocess.Popen(["systemctl", "--user", "stop", "vanessa.service"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        QApplication.instance().quit()
        os._exit(0)


def main():
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --ignore-gpu-blocklist --no-sandbox --disable-wasm-trap-handler --disable-gpu-watchdog --disable-dev-shm-usage"
    app = QApplication(sys.argv)
    app.setApplicationName("vanessa_desktop")
    app.setQuitOnLastWindowClosed(False)

    overlay = VanessaDesktopOverlay()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
