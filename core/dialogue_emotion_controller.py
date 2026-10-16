import time
import re
from typing import Dict, Any, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class DialogueEmotionController(QObject):
    command_packet_ready = pyqtSignal(dict)
    balloon_requested = pyqtSignal(str, int)

    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.current_mood = "relaxed"
        self.current_arousal = 0.5
        self.current_intent = "IDLE"
        self.last_packet: Dict[str, Any] = {}

    def map_emotion_to_blendshapes(self, emotion_name: str, intensity: float = 1.0) -> Dict[str, float]:
        name_clean = emotion_name.lower().strip()
        weights = {
            "happy": 0.0,
            "relaxed": 0.0,
            "surprised": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "pout": 0.0,
            "thinking": 0.0,
            "listen_attentive": 0.0
        }
        val = max(0.0, min(1.0, float(intensity)))
        if name_clean in ("happy", "joy", "smile"):
            weights["happy"] = val
        elif name_clean in ("surprised", "shocked"):
            weights["surprised"] = val
        elif name_clean in ("pout", "annoyed", "mischievous"):
            weights["pout"] = val
            weights["angry"] = val * 0.4
        elif name_clean in ("thinking", "curious"):
            weights["thinking"] = val
        elif name_clean in ("listen_attentive", "listen"):
            weights["listen_attentive"] = val
        elif name_clean in ("sad", "unhappy"):
            weights["sad"] = val
        else:
            weights["relaxed"] = val
        return weights

    def build_command_packet(
        self,
        action: str = "idle",
        target_coords: Optional[Tuple[float, float, float]] = None,
        emotion: str = "relaxed",
        emotion_intensity: float = 1.0,
        voice_id: str = "dalia_anime",
        avatar_mode: str = "standard"
    ) -> Dict[str, Any]:
        coords = list(target_coords) if target_coords is not None else [0.0, 0.0, 0.0]
        blendshapes = self.map_emotion_to_blendshapes(emotion, emotion_intensity)
        packet = {
            "timestamp": time.time(),
            "action": action,
            "target_coords": coords,
            "emotion": {
                "mood": emotion,
                "arousal": self.current_arousal,
                "intent": self.current_intent,
                "intensity": emotion_intensity
            },
            "voice_id": voice_id,
            "blendshapes_weights": blendshapes,
            "avatar_mode": avatar_mode
        }
        self.last_packet = packet
        self.command_packet_ready.emit(packet)
        return packet

    def present_dialogue(self, text: str, duration_ms: Optional[int] = None, emotion: Optional[str] = None):
        clean_text = re.sub(r"\*[^*]*\*", "", text)
        clean_text = re.sub(r"[*_#`~]", "", clean_text).strip()
        if not clean_text:
            clean_text = text.strip()
        if len(clean_text) > 320:
            clean_text = clean_text[:317] + "..."
        read_duration = duration_ms if duration_ms is not None else max(4500, min(18000, len(clean_text) * 75 + 2500))
        if hasattr(self.overlay, "show_balloon"):
            self.overlay.show_balloon(clean_text, duration_ms=read_duration)
        self.balloon_requested.emit(clean_text, read_duration)

        if emotion and hasattr(self.overlay, "vrm_widget") and self.overlay.vrm_widget:
            self.overlay.vrm_widget.set_expression(emotion, 1.0)
            QTimer.singleShot(read_duration, lambda: self.overlay.vrm_widget.set_expression("relaxed", 0.7))
