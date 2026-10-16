import os
import json
import urllib.request
from typing import Dict, Any, Optional

class SemanticVisionConnector:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def infer_intent_from_window(self, win_title: str, win_class: str) -> Dict[str, Any]:
        cls = (win_class or "").lower()
        title = (win_title or "").lower()
        if any(term in cls or term in title for term in ["nvim", "vim", "code", "terminal", "kitty", "foot", "alacritty"]):
            return {
                "category": "developer",
                "recommended_intent": "THINK_AND_INSPECT",
                "posture": "curious_lean",
                "speed": 0.0,
                "urgency": 0.6
            }
        elif any(term in cls or term in title for term in ["youtube", "mpv", "spotify", "video", "twitch", "netflix"]):
            return {
                "category": "media",
                "recommended_intent": "SIT_ON_EDGE",
                "posture": "sit_casual",
                "speed": 0.0,
                "urgency": 0.3
            }
        elif any(term in cls or term in title for term in ["browser", "firefox", "chrome", "zen", "chromium"]):
            return {
                "category": "reading",
                "recommended_intent": "WALK_TO_LEDGE",
                "posture": "locomotion",
                "speed": 0.8,
                "urgency": 0.7
            }
        return {
            "category": "standby",
            "recommended_intent": "IDLE_LEDGE",
            "posture": "standby",
            "speed": 0.0,
            "urgency": 0.2
        }
