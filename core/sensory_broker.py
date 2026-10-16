import time
from enum import Enum, IntEnum
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Callable, Dict, Any

class SensoryEventType(str, Enum):
    SCREEN_CONTEXT = "screen_context"
    TEXT_STIMULUS = "text_stimulus"
    MEDIA_STREAM = "media_stream"
    CURSOR_PROXIMITY = "cursor_proximity"

class EmotionalTier(IntEnum):
    TIER_1_BASELINE = 1
    TIER_2_EXAGGERATED = 2
    TIER_3_CHIBI_MORPH = 3

@dataclass(frozen=True)
class ScreenContextEvent:
    window_id: str
    app_class: str
    title: str
    bounding_box: Tuple[int, int, int, int]
    focus_state: bool
    timestamp: float

@dataclass(frozen=True)
class TextStimulusEvent:
    content_category: str
    emotional_valence: float
    arousal: float
    intensity: float
    raw_text: str
    timestamp: float

@dataclass(frozen=True)
class MediaStreamEvent:
    media_type: str
    title: str
    artist: str
    perceived_loudness: float
    tempo_bpm: float
    duration_sec: float
    timestamp: float

@dataclass(frozen=True)
class CursorProximityEvent:
    cursor_x: float
    cursor_y: float
    velocity_x: float
    velocity_y: float
    distance_to_avatar: float
    timestamp: float

class SensoryBroker:
    _instance: Optional['SensoryBroker'] = None

    def __init__(self):
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._last_salience: float = 0.0
        self._current_tier: EmotionalTier = EmotionalTier.TIER_1_BASELINE
        self._vrm_widget: Optional[Any] = None

    @classmethod
    def get_instance(cls) -> 'SensoryBroker':
        if cls._instance is None:
            cls._instance = SensoryBroker()
        return cls._instance

    def set_vrm_widget(self, widget: Any):
        self._vrm_widget = widget

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def calculate_salience(self, valence: float, arousal: float, intensity: float) -> float:
        val_mag = min(1.0, max(0.0, abs(valence)))
        arousal_mag = min(1.0, max(0.0, arousal))
        int_mag = min(1.0, max(0.0, intensity))
        score = (0.35 * val_mag) + (0.40 * arousal_mag) + (0.25 * int_mag)
        return min(1.0, max(0.0, score))

    def evaluate_tier(self, salience: float) -> EmotionalTier:
        if salience >= 0.78:
            return EmotionalTier.TIER_3_CHIBI_MORPH
        elif salience >= 0.40:
            return EmotionalTier.TIER_2_EXAGGERATED
        return EmotionalTier.TIER_1_BASELINE

    def dispatch_screen_context(
        self,
        window_id: str,
        app_class: str,
        title: str,
        bbox: Tuple[int, int, int, int],
        focus_state: bool
    ):
        event = ScreenContextEvent(
            window_id=str(window_id),
            app_class=str(app_class),
            title=str(title),
            bounding_box=bbox,
            focus_state=bool(focus_state),
            timestamp=time.time()
        )
        salience = 0.45 if focus_state else 0.20
        payload = {
            "type": SensoryEventType.SCREEN_CONTEXT.value,
            "data": asdict(event),
            "salience": salience,
            "tier": int(self.evaluate_tier(salience))
        }
        self._publish(payload)

    def dispatch_text_stimulus(
        self,
        category: str,
        valence: float,
        arousal: float,
        intensity: float,
        raw_text: str
    ):
        event = TextStimulusEvent(
            content_category=str(category),
            emotional_valence=float(valence),
            arousal=float(arousal),
            intensity=float(intensity),
            raw_text=str(raw_text),
            timestamp=time.time()
        )
        salience = self.calculate_salience(valence, arousal, intensity)
        self._last_salience = salience
        self._current_tier = self.evaluate_tier(salience)
        payload = {
            "type": SensoryEventType.TEXT_STIMULUS.value,
            "data": asdict(event),
            "salience": salience,
            "tier": int(self._current_tier)
        }
        self._publish(payload)

    def dispatch_media_stream(
        self,
        media_type: str,
        title: str,
        artist: str,
        loudness: float,
        bpm: float,
        duration: float
    ):
        event = MediaStreamEvent(
            media_type=str(media_type),
            title=str(title),
            artist=str(artist),
            perceived_loudness=float(loudness),
            tempo_bpm=float(bpm),
            duration_sec=float(duration),
            timestamp=time.time()
        )
        salience = min(1.0, max(0.1, loudness * 0.7 + (min(160.0, bpm) / 160.0) * 0.3))
        payload = {
            "type": SensoryEventType.MEDIA_STREAM.value,
            "data": asdict(event),
            "salience": salience,
            "tier": int(self.evaluate_tier(salience))
        }
        self._publish(payload)

    def dispatch_cursor_proximity(
        self,
        cx: float,
        cy: float,
        vx: float,
        vy: float,
        dist: float
    ):
        event = CursorProximityEvent(
            cursor_x=float(cx),
            cursor_y=float(cy),
            velocity_x=float(vx),
            velocity_y=float(vy),
            distance_to_avatar=float(dist),
            timestamp=time.time()
        )
        salience = max(0.0, min(1.0, 1.0 - (dist / 800.0))) if dist < 800 else 0.05
        payload = {
            "type": SensoryEventType.CURSOR_PROXIMITY.value,
            "data": asdict(event),
            "salience": salience,
            "tier": int(self.evaluate_tier(salience))
        }
        self._publish(payload)

    def _publish(self, payload: Dict[str, Any]):
        for sub in self._subscribers:
            try:
                sub(payload)
            except Exception:
                pass
        if self._vrm_widget and hasattr(self._vrm_widget, "dispatch_sensory_event"):
            try:
                self._vrm_widget.dispatch_sensory_event(payload)
            except Exception:
                pass
