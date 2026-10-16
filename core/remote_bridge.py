import os
import json
import time
import asyncio
import threading
import logging
from typing import Dict, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("RemoteBridge")
logger.setLevel(logging.INFO)

class RemoteCloudBridge(QObject):
    response_received = pyqtSignal(str, str, str)
    connection_changed = pyqtSignal(bool, str)
    omni_notification = pyqtSignal(str, dict)

    def __init__(self, config_path: str = "config/cloud_config.json", parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.config = self._load_config()

        self.is_connected = False
        self._running = False
        self._ws_client = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        server_cfg = self.config.get("server", {})
        self.enabled = server_cfg.get("enabled", False)
        self.host = server_cfg.get("host", "127.0.0.1")
        self.port = server_cfg.get("port", 8765)
        self.token = server_cfg.get("auth_token", "vanessa_secret")
        self.public_url = server_cfg.get("public_url", "")
        self.use_ssl = server_cfg.get("use_ssl", False)

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.config_path}: {e}")
        return {
            "server": {
                "enabled": False,
                "host": "127.0.0.1",
                "port": 8765,
                "auth_token": "vanessa_secret",
                "use_ssl": False,
                "public_url": ""
            }
        }

    def start(self):
        if not self.enabled or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _get_ws_url(self) -> str:
        if self.public_url:
            base = self.public_url.replace("https://", "wss://").replace("http://", "ws://")
            return f"{base}/ws/vanessa/client?token={self.token}"
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/ws/vanessa/client?token={self.token}"

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._maintain_connection())

    async def _maintain_connection(self):
        import aiohttp
        ws_url = self._get_ws_url()

        while self._running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url, timeout=10) as ws:
                        self._ws_client = ws
                        self.is_connected = True
                        self.connection_changed.emit(True, "Conectado a Vanessa Cloud Server")
                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                self._handle_incoming_frame(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception:
                self.is_connected = False
                self._ws_client = None

            self.is_connected = False
            self._ws_client = None
            await asyncio.sleep(15)

    def _handle_incoming_frame(self, raw_text: str):
        try:
            data = json.loads(raw_text)
            msg_type = data.get("type")

            if msg_type == "vanessa_response":
                reply = data.get("reply", "")
                emotion = data.get("emotion", "relaxed")
                action = data.get("action", "idle")
                self.response_received.emit(reply, emotion, action)

            elif msg_type == "omni_notification":
                event_name = data.get("event", "generic")
                payload = data.get("payload", {})
                self.omni_notification.emit(event_name, payload)

            elif msg_type == "handshake_ok":
                logger.info("Handshake confirmed with Cloud Server.")
        except Exception:
            pass

    def send_chat_message(self, user_text: str, context: Optional[dict] = None) -> bool:
        if not self.is_connected or not self._loop:
            return False

        payload = {
            "type": "chat_message",
            "text": user_text,
            "context": context or {},
            "timestamp": time.time()
        }

        asyncio.run_coroutine_threadsafe(self._async_send(payload), self._loop)
        return True

    def send_system_telemetry(self, telemetry_data: dict) -> bool:
        if not self.is_connected or not self._loop:
            return False

        payload = {
            "type": "telemetry_update",
            "telemetry": telemetry_data,
            "timestamp": time.time()
        }

        asyncio.run_coroutine_threadsafe(self._async_send(payload), self._loop)
        return True

    async def _async_send(self, payload: dict):
        if self._ws_client and not self._ws_client.closed:
            try:
                await self._ws_client.send_str(json.dumps(payload))
            except Exception:
                pass
