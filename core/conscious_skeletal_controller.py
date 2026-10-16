import time
import math
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class ConsciousSkeletalController(QObject):
    skeletal_packet_emitted = pyqtSignal(dict)

    def __init__(self, overlay=None):
        parent_obj = overlay if isinstance(overlay, QObject) else None
        super().__init__(parent_obj)
        self.overlay = overlay

        self.dialogue_role = "none"
        self.dialogue_intent = "idle"
        self.dialogue_emotion = "neutral"
        self.dialogue_text = ""
        self.head_tilt_target = [0.0, 0.0, 0.0]
        self.facial_preset = "neutral"
        self.facial_intensity = 1.0

        self.desktop_category = "desktop"
        self.active_window_title = ""
        self.active_window_class = ""
        self.inactive_windows_count = 0
        self.is_fullscreen = False
        self.desktop_focus_point = [0.5, 0.5]

        self.media_type = "none"
        self.media_title = ""
        self.media_artist = ""
        self.media_playing = False
        self.media_tempo_bpm = 120.0
        self.rhythm_phase = 0.0

        self.haptic_state = "idle"
        self.haptic_timer = 0.0
        self.inertia_lean = [0.0, 0.0]
        self.squash_factor = 1.0

        self.pc_idle_seconds = 0.0
        self.vanessa_idle_seconds = 0.0
        self.dual_idle_mode = "active_dialogue"

        self.contrapposto_shift = 0.0
        self.contrapposto_timer = 0.0
        self.spine_lean = [0.0, 0.0, 0.0]
        self.arm_relaxation = 0.85
        self.knee_flexion = 0.04

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(100)

    def handle_conversation_turn(self, role: str, text: str, emotion: str = "", intent: str = ""):
        self.vanessa_idle_seconds = 0.0
        self.dialogue_role = str(role or "").lower()
        self.dialogue_text = str(text or "")
        lower_text = self.dialogue_text.lower()

        if emotion:
            self.dialogue_emotion = emotion.lower()
        elif any(w in lower_text for w in ["gracias", "feliz", "excelente", "jaja", "jeje", "bien"]):
            self.dialogue_emotion = "happy"
        elif any(w in lower_text for w in ["pero", "espera", "seguro", "quizas", "tal vez"]):
            self.dialogue_emotion = "curious"
        elif any(w in lower_text for w in ["error", "fallo", "problema", "cuidado", "alerta"]):
            self.dialogue_emotion = "surprised"
        else:
            self.dialogue_emotion = "neutral"

        if intent:
            self.dialogue_intent = intent.lower()
        elif "?" in self.dialogue_text or "¿" in self.dialogue_text:
            self.dialogue_intent = "question"
        elif "!" in self.dialogue_text or "¡" in self.dialogue_text:
            self.dialogue_intent = "exclamation"
        elif self.dialogue_role == "assistant":
            self.dialogue_intent = "answer"
        else:
            self.dialogue_intent = "statement"

        if self.dialogue_intent == "question":
            self.head_tilt_target = [0.06, 0.12, 0.08]
            self.facial_preset = "curious"
            self.facial_intensity = 0.85
            self.spine_lean = [0.04, 0.0, 0.0]
        elif self.dialogue_emotion == "happy":
            self.head_tilt_target = [-0.04, 0.0, 0.0]
            self.facial_preset = "joy"
            self.facial_intensity = 0.95
            self.spine_lean = [-0.02, 0.0, 0.0]
        elif self.dialogue_emotion == "curious":
            self.head_tilt_target = [0.04, -0.10, 0.06]
            self.facial_preset = "thinking"
            self.facial_intensity = 0.8
            self.spine_lean = [0.03, 0.0, 0.0]
        elif self.dialogue_emotion == "surprised":
            self.head_tilt_target = [-0.08, 0.0, 0.0]
            self.facial_preset = "surprised"
            self.facial_intensity = 0.9
            self.spine_lean = [-0.05, 0.0, 0.0]
        elif self.dialogue_role == "assistant":
            self.head_tilt_target = [0.02, 0.04, 0.02]
            self.facial_preset = "neutral"
            self.facial_intensity = 1.0
            self.spine_lean = [0.01, 0.0, 0.0]
        else:
            self.head_tilt_target = [0.0, 0.0, 0.0]
            self.facial_preset = "neutral"
            self.facial_intensity = 1.0
            self.spine_lean = [0.0, 0.0, 0.0]

        self.dispatch()

    def update_desktop_context(self, active_title: str, active_class: str, inactive_windows: Optional[List[Any]] = None, is_fullscreen: bool = False):
        self.active_window_title = str(active_title or "")
        self.active_window_class = str(active_class or "")
        self.inactive_windows_count = len(inactive_windows) if inactive_windows else 0
        self.is_fullscreen = bool(is_fullscreen)

        cls_lower = self.active_window_class.lower()
        title_lower = self.active_window_title.lower()

        if any(c in cls_lower or c in title_lower for c in ["code", "nvim", "vim", "kitty", "alacritty", "terminal", "bash", "sublime"]):
            self.desktop_category = "ide"
            self.desktop_focus_point = [0.4, 0.45]
        elif any(c in cls_lower or c in title_lower for c in ["firefox", "chrome", "chromium", "brave", "edge"]):
            self.desktop_category = "browser"
            self.desktop_focus_point = [0.5, 0.4]
        elif any(c in cls_lower or c in title_lower for c in ["mpv", "vlc", "youtube", "netflix", "twitch"]):
            self.desktop_category = "media_player"
            self.desktop_focus_point = [0.6, 0.5]
        elif any(c in cls_lower or c in title_lower for c in ["steam", "zenless", "genshin", "game"]):
            self.desktop_category = "gaming"
            self.desktop_focus_point = [0.5, 0.5]
        else:
            self.desktop_category = "desktop"
            self.desktop_focus_point = [0.5, 0.5]

        if self.desktop_category == "ide" and self.vanessa_idle_seconds > 45:
            self.spine_lean[0] = 0.03
        elif self.desktop_category == "gaming":
            self.spine_lean[0] = -0.02

        self.dispatch()

    def update_media_context(self, media_type: str, title: str = "", artist: str = "", is_playing: bool = False, tempo_bpm: float = 120.0):
        t_clean = str(media_type or "none").lower()
        if t_clean not in ["music", "audio", "video", "none"]:
            t_clean = "none"
        self.media_type = t_clean
        self.media_title = str(title or "")
        self.media_artist = str(artist or "")
        self.media_playing = bool(is_playing)
        self.media_tempo_bpm = max(40.0, min(240.0, float(tempo_bpm or 120.0)))
        self.dispatch()

    def handle_haptic_interaction(self, event_type: str, x: float = 0.0, y: float = 0.0, dx: float = 0.0, dy: float = 0.0):
        self.vanessa_idle_seconds = 0.0
        self.pc_idle_seconds = 0.0
        ev = str(event_type or "click").lower()
        self.haptic_state = ev
        self.haptic_timer = 1.5

        if ev == "head_pat":
            self.facial_preset = "joy"
            self.facial_intensity = 1.0
            self.head_tilt_target = [-0.10, 0.0, 0.0]
            self.squash_factor = 0.96
            self.spine_lean = [-0.03, 0.0, 0.0]
        elif ev in ["body_click", "click"]:
            self.facial_preset = "surprised"
            self.facial_intensity = 0.65
            self.head_tilt_target = [0.04, 0.05, 0.0]
            self.squash_factor = 0.98
        elif ev in ["drag_start", "drag_move"]:
            self.facial_preset = "curious"
            self.facial_intensity = 0.75
            clamp_dx = max(-0.25, min(0.25, dx * 0.01))
            clamp_dy = max(-0.25, min(0.25, dy * 0.01))
            self.inertia_lean = [-clamp_dx, -clamp_dy]
            self.squash_factor = 1.04
        elif ev == "drag_release":
            self.inertia_lean = [0.0, 0.0]
            self.squash_factor = 0.97

        self.dispatch()

    def update_inactivity_timers(self, pc_idle_seconds: float, vanessa_idle_seconds: float):
        self.pc_idle_seconds = max(0.0, float(pc_idle_seconds))
        self.vanessa_idle_seconds = max(0.0, float(vanessa_idle_seconds))

        if self.pc_idle_seconds > 240.0:
            self.dual_idle_mode = "system_sleep"
            self.facial_preset = "neutral"
            self.facial_intensity = 0.5
            self.head_tilt_target = [0.12, 0.0, 0.0]
            self.spine_lean = [0.05, 0.0, 0.0]
            self.arm_relaxation = 0.95
        elif self.vanessa_idle_seconds > 90.0 and self.pc_idle_seconds < 45.0:
            self.dual_idle_mode = "companion_working"
            self.facial_preset = "neutral"
            self.facial_intensity = 0.9
            self.head_tilt_target = [0.04, 0.06, 0.04]
            self.arm_relaxation = 0.85
        elif self.vanessa_idle_seconds > 45.0:
            self.dual_idle_mode = "curious_fidget"
            self.facial_preset = "neutral"
            self.facial_intensity = 1.0
        else:
            self.dual_idle_mode = "active_dialogue"

        self.dispatch()

    def _on_tick(self):
        dt = 0.1
        self.pc_idle_seconds += dt
        self.vanessa_idle_seconds += dt

        self.contrapposto_timer += dt
        self.contrapposto_shift = math.sin(self.contrapposto_timer * 0.35) * 0.45

        if self.haptic_timer > 0.0:
            self.haptic_timer = max(0.0, self.haptic_timer - dt)
            if self.haptic_timer == 0.0:
                self.haptic_state = "idle"
                self.squash_factor = 1.0
                self.inertia_lean = [0.0, 0.0]

        if self.media_playing and self.media_type == "music":
            bps = self.media_tempo_bpm / 60.0
            self.rhythm_phase = (self.rhythm_phase + dt * bps * 2.0 * math.pi) % (2.0 * math.pi)

        self.update_inactivity_timers(self.pc_idle_seconds, self.vanessa_idle_seconds)

    def compute_packet(self) -> Dict[str, Any]:
        music_sway_y = 0.0
        music_sway_z = 0.0
        if self.media_playing and self.media_type == "music":
            music_sway_y = math.sin(self.rhythm_phase) * 0.06
            music_sway_z = math.sin(self.rhythm_phase * 0.5) * 0.03

        head_pitch = self.head_tilt_target[0]
        head_yaw = self.head_tilt_target[1] + music_sway_y
        head_roll = self.head_tilt_target[2] + music_sway_z

        tactical_active = False
        if self.overlay and hasattr(self.overlay, "protection_manager") and self.overlay.protection_manager:
            tactical_active = getattr(self.overlay.protection_manager, "is_active", False)

        return {
            "channel1_conversation": {
                "role": self.dialogue_role,
                "intent": self.dialogue_intent,
                "emotion": self.dialogue_emotion,
                "text_snippet": self.dialogue_text[:60]
            },
            "channel2_desktop": {
                "category": self.desktop_category,
                "active_class": self.active_window_class,
                "inactive_count": self.inactive_windows_count,
                "focus_point": self.desktop_focus_point,
                "is_fullscreen": self.is_fullscreen
            },
            "channel3_media": {
                "type": self.media_type,
                "title": self.media_title,
                "artist": self.media_artist,
                "is_playing": self.media_playing,
                "tempo_bpm": self.media_tempo_bpm,
                "sway_enabled": (self.media_playing and self.media_type == "music")
            },
            "channel4_haptics": {
                "state": self.haptic_state,
                "inertia_lean": self.inertia_lean,
                "squash_factor": self.squash_factor
            },
            "channel5_dual_idle": {
                "pc_idle_seconds": round(self.pc_idle_seconds, 2),
                "vanessa_idle_seconds": round(self.vanessa_idle_seconds, 2),
                "mode": self.dual_idle_mode
            },
            "channel6_tactical": {
                "active": tactical_active
            },
            "biomechanical_pose": {
                "head_tilt": [head_pitch, head_yaw, head_roll],
                "spine_lean": self.spine_lean,
                "contrapposto_shift": round(self.contrapposto_shift, 3),
                "arm_relaxation": self.arm_relaxation,
                "knee_flexion": self.knee_flexion,
                "facial_preset": self.facial_preset,
                "facial_intensity": self.facial_intensity
            }
        }

    def dispatch(self):
        packet = self.compute_packet()
        self.skeletal_packet_emitted.emit(packet)
        if self.overlay and hasattr(self.overlay, "vrm_widget") and self.overlay.vrm_widget:
            self.overlay.vrm_widget.apply_conscious_skeletal_packet(packet)
