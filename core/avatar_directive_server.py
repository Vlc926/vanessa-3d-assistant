import asyncio
import json
import threading
from typing import Set, Dict, Any, Optional
import websockets

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
                "look_target": "user_camera"
            }
            await websocket.send(json.dumps(init_packet))
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if self.on_client_message:
                        self.on_client_message(data)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.clients.discard(websocket)

    def broadcast(self, payload: Dict[str, Any]):
        if not self.loop or not self.clients:
            return
        msg = json.dumps(payload)
        asyncio.run_coroutine_threadsafe(self._broadcast_async(msg), self.loop)

    async def _broadcast_async(self, message: str):
        if not self.clients:
            return
        coros = [ws.send(message) for ws in list(self.clients)]
        results = await asyncio.gather(*coros, return_exceptions=True)

    def set_state(self, state: str):
        self.current_state = state
        self.broadcast({
            "type": "avatar_directive",
            "state": state
        })

    def emit_directive(
        self,
        state: str,
        emotion_vector: Optional[Dict[str, float]] = None,
        body_gesture: str = "idle",
        look_target: str = "user_camera",
        dialogue_text: str = "",
        audio_base64: str = ""
    ):
        self.current_state = state
        if emotion_vector:
            self.current_emotion = emotion_vector
        payload = {
            "type": "avatar_directive",
            "state": state,
            "emotion_vector": self.current_emotion,
            "body_gesture": body_gesture,
            "look_target": look_target,
            "dialogue_text": dialogue_text,
            "audio_base64": audio_base64
        }
        self.broadcast(payload)

    def stop(self):
        self.is_running = False
        if self.server and self.loop:
            self.server.close()
            self.loop.call_soon_threadsafe(self.loop.stop)
