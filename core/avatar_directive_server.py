import asyncio
import json
import math
import os
import time
import threading
from typing import Set, Dict, Any, Optional, Tuple, List
import websockets


class SmartLocomotionRouter:
    WALK_THRESHOLD_PX = 650.0

    @classmethod
    def evaluate_route(
        cls,
        start_pos: Any,
        target_pos: Any = None,
        urgency: float = 0.2,
        tone: str = "relaxed",
        window_gaps: int = 0
    ) -> Dict[str, Any]:
        if target_pos is None or isinstance(start_pos, (int, float)):
            dist = float(start_pos)
            dx = dist
            dy = 0.0
        else:
            dx = float(target_pos[0]) - float(start_pos[0])
            dy = float(target_pos[1]) - float(start_pos[1])
            dist = math.hypot(dx, dy)
        tone_lower = str(tone or "relaxed").lower()
        urgent_tones = {"urgent", "immediate", "alert", "panic", "high", "fast", "emergency", "media", "action", "button"}
        is_urgent = (float(urgency) >= 0.70) or (tone_lower in urgent_tones)

        if window_gaps > 0 and 300.0 <= dist < 900.0 and not is_urgent:
            mode = "HYBRID_INTERLEAVED"
            sub_mode = "JOG"
            anticipation_sec = 0.06
            transition_sec = 0.12
            stride_freq = 2.4
        elif is_urgent or dist >= cls.WALK_THRESHOLD_PX:
            mode = "TELEPORT_TRANSITION"
            sub_mode = "TELEPORT"
            anticipation_sec = 0.08
            transition_sec = 0.12
            stride_freq = 3.2
        else:
            sub_mode = "WALK" if dist < 420.0 and float(urgency) < 0.45 else "JOG"
            mode = sub_mode
            anticipation_sec = 0.0
            speed_px = 165.0 if sub_mode == "WALK" else 240.0
            transition_sec = max(0.35, dist / speed_px)
            stride_freq = 1.85 if sub_mode == "WALK" else 2.65

        return {
            "mode": mode,
            "sub_mode": sub_mode,
            "locomotion_mode": mode,
            "distance_px": round(dist, 2),
            "dx": round(dx, 2),
            "dy": round(dy, 2),
            "urgency": round(float(urgency), 3),
            "tone": tone_lower,
            "anticipation_sec": anticipation_sec,
            "cut_sec": round(transition_sec, 3),
            "transition_sec": round(transition_sec, 3),
            "stride_frequency": stride_freq,
            "clip": "walk_forward" if mode in ("WALK", "JOG") else "jump"
        }


class AvatarDirectiveServer:
    _instance: Optional['AvatarDirectiveServer'] = None

    @classmethod
    def get_instance(cls, host: str = "127.0.0.1", port: int = 8765) -> 'AvatarDirectiveServer':
        if cls._instance is None:
            cls._instance = AvatarDirectiveServer(host, port)
        return cls._instance

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.server = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.current_state = "IDLE"
        self.current_emotion = {
            "joy": 0.0,
            "curiosity": 0.0,
            "surprise": 0.0,
            "tension": 0.0,
            "confidence": 0.5,
            "shyness": 0.0
        }
        self.on_client_message = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.learned_behaviors_path = os.path.join(base_dir, "config", "learned_behaviors.json")
        self.learned_behaviors = self.load_learned_behaviors()

    def load_learned_behaviors(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.learned_behaviors_path):
                with open(self.learned_behaviors_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "learned_expressions" in data:
                        return data
        except Exception:
            pass
        return {"version": "1.0", "evolution_count": 0, "learned_expressions": []}

    def record_learned_behavior(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(entry, dict):
            return self.learned_behaviors
        expr_list: List[Dict[str, Any]] = self.learned_behaviors.setdefault("learned_expressions", [])
        entry_id = entry.get("id") or f"synth_{int(time.time() * 1000)}"
        entry["id"] = entry_id
        existing_ids = {item.get("id") for item in expr_list if isinstance(item, dict)}
        if entry_id not in existing_ids:
            expr_list.append(entry)
            if len(expr_list) > 120:
                expr_list.pop(0)
            self.learned_behaviors["evolution_count"] = int(self.learned_behaviors.get("evolution_count", 0)) + 1
            try:
                os.makedirs(os.path.dirname(self.learned_behaviors_path), exist_ok=True)
                with open(self.learned_behaviors_path, "w", encoding="utf-8") as f:
                    json.dump(self.learned_behaviors, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        return self.learned_behaviors

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        async def _start():
            for p in range(self.port, self.port + 15):
                try:
                    self.server = await websockets.serve(self._handler, self.host, p)
                    self.port = p
                    break
                except Exception:
                    continue
        self.loop.run_until_complete(_start())
        if self.server:
            self.loop.run_forever()

    async def _handler(self, websocket):
        self.clients.add(websocket)
        try:
            init_packet = {
                "type": "avatar_directive",
                "state": self.current_state,
                "emotion_vector": self.current_emotion,
                "body_gesture": "idle",
                "look_target": "user_camera",
                "full_body_articulation": self._compute_full_body_articulation(self.current_state, self.current_emotion, "idle"),
                "learned_behaviors": self.learned_behaviors.get("learned_expressions", [])[-15:]
            }
            await websocket.send(json.dumps(init_packet))
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if isinstance(data, dict) and data.get("type") == "save_learned_behavior":
                        behavior = data.get("behavior")
                        if isinstance(behavior, dict):
                            self.record_learned_behavior(behavior)
                    if self.on_client_message:
                        self.on_client_message(data)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)

    def _compute_full_body_articulation(self, state: str, emotion: Dict[str, float], gesture: str) -> Dict[str, Any]:
        joy = float(emotion.get("joy", 0.0))
        curiosity = float(emotion.get("curiosity", 0.0))
        surprise = float(emotion.get("surprise", 0.0))
        tension = float(emotion.get("tension", 0.0))
        shyness = float(emotion.get("shyness", 0.0))

        pelvis_sway = 0.035 * (1.0 + joy * 0.5)
        spine_pitch = 0.04 * curiosity - 0.05 * surprise + 0.03 * shyness
        chest_lift = 0.04 * joy + 0.03 * surprise - 0.02 * shyness
        shoulder_drop = 0.05 * shyness - 0.04 * tension
        knee_flex = 0.04 + 0.03 * surprise + 0.02 * joy

        return {
            "pelvis": {"sway": round(pelvis_sway, 4), "bob": round(0.015 * joy, 4)},
            "spine": {"pitch": round(spine_pitch, 4), "roll": round(0.02 * curiosity, 4)},
            "chest": {"pitch": round(chest_lift, 4)},
            "shoulders": {"drop": round(shoulder_drop, 4)},
            "arms": {"spread": round(0.06 * joy - 0.05 * shyness, 4), "elbow_bend": round(0.21 + 0.12 * shyness, 4)},
            "legs": {"knee_flex": round(knee_flex, 4), "stance_width": round(0.03 * (1.0 - shyness * 0.5), 4)},
            "gesture_clip": gesture or "idle"
        }

    def broadcast(self, payload: Dict[str, Any]):
        if not self.loop or not self.clients:
            return
        msg = json.dumps(payload)
        asyncio.run_coroutine_threadsafe(self._broadcast_async(msg), self.loop)

    async def _broadcast_async(self, message: str):
        if not self.clients:
            return
        coros = [ws.send(message) for ws in list(self.clients)]
        await asyncio.gather(*coros, return_exceptions=True)

    def set_state(self, state: str):
        self.current_state = state
        self.broadcast({
            "type": "avatar_directive",
            "state": state,
            "full_body_articulation": self._compute_full_body_articulation(state, self.current_emotion, "idle")
        })

    def route_locomotion(
        self,
        start_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        urgency: float = 0.2,
        tone: str = "relaxed",
        window_gaps: int = 0
    ) -> Dict[str, Any]:
        route = SmartLocomotionRouter.evaluate_route(start_pos, target_pos, urgency, tone, window_gaps)
        self.broadcast({
            "type": "avatar_directive",
            "state": "LOCOMOTION",
            "locomotion_route": route,
            "body_gesture": route["clip"]
        })
        return route

    def emit_directive(
        self,
        state: str,
        emotion_vector: Optional[Dict[str, float]] = None,
        body_gesture: str = "idle",
        look_target: str = "user_camera",
        dialogue_text: str = "",
        audio_base64: str = "",
        locomotion_route: Optional[Dict[str, Any]] = None
    ):
        self.current_state = state
        if emotion_vector:
            self.current_emotion = emotion_vector
        articulation = self._compute_full_body_articulation(state, self.current_emotion, body_gesture)
        payload = {
            "type": "avatar_directive",
            "state": state,
            "emotion_vector": self.current_emotion,
            "body_gesture": body_gesture,
            "look_target": look_target,
            "dialogue_text": dialogue_text,
            "audio_base64": audio_base64,
            "full_body_articulation": articulation
        }
        if locomotion_route:
            payload["locomotion_route"] = locomotion_route
        self.broadcast(payload)

    def stop(self):
        self.is_running = False
        if self.server and self.loop:
            self.server.close()
            self.loop.call_soon_threadsafe(self.loop.stop)
