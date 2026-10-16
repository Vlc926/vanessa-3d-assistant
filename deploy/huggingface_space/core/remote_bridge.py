"""
Remote Cloud Bridge for Vanessa Desktop Thin Client.
Connects the local PyQt6 / Hyprland desktop assistant to the high-performance
remote Cloud Server via WebSocket.
Provides:
- Non-blocking asynchronous bidirectional communication.
- Instant fallback to local execution if network drops.
- Signals for responses, mood changes, animations, and omni notifications.
"""

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
    # Signals to communicate cleanly with PyQt6 GUI in vanessa_desktop.py
    response_received = pyqtSignal(str, str, str)  # reply, emotion, action
    connection_changed = pyqtSignal(bool, str)     # is_connected, status_message
    omni_notification = pyqtSignal(str, dict)      # event_name, payload

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
                "host": "127.0.0.1",
                "port": 8765,
                "auth_token": "vanessa_secret",
                "use_ssl": False,
                "public_url": ""
            }
        }

    def start(self):
        """Starts the background worker thread for WebSocket communication."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        logger.info("RemoteCloudBridge thread launched.")

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
                logger.info(f"Connecting to Vanessa Cloud Server at {ws_url}...")
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url, timeout=10) as ws:
                        self._ws_client = ws
                        self.is_connected = True
                        self.connection_changed.emit(True, "Conectado a Vanessa Cloud Server (Potencia Remota Activa)")
                        logger.info("Successfully connected to Vanessa Cloud Server!")

                        async for msg in ws:
                            if not self._running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                self._handle_incoming_frame(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

            except Exception as e:
                self.is_connected = False
                self._ws_client = None
                self.connection_changed.emit(False, f"Sin conexión al servidor remoto ({e}). Modo local de reserva.")
                logger.warning(f"Connection lost or failed: {e}. Retrying in 5 seconds...")

            self.is_connected = False
            self._ws_client = None
            await asyncio.sleep(5)

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
                logger.info(f"Handshake acknowledged: {data.get('message')}")

        except Exception as e:
            logger.error(f"Error parsing frame from cloud: {e}")

    def send_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Sends user query to remote cloud brain."""
        if not self.is_connected or not self._ws_client or not self._loop:
            return False

        payload = {
            "type": "user_prompt",
            "prompt": prompt,
            "context": context or {},
            "timestamp": time.time()
        }
        asyncio.run_coroutine_threadsafe(
            self._ws_client.send_str(json.dumps(payload)),
            self._loop
        )
        return True

    def send_screen_update(self, active_window: str):
        """Sends lightweight active window info to cloud brain."""
        if not self.is_connected or not self._ws_client or not self._loop:
            return

        payload = {
            "type": "screen_update",
            "active_window": active_window,
            "timestamp": time.time()
        }
        asyncio.run_coroutine_threadsafe(
            self._ws_client.send_str(json.dumps(payload)),
            self._loop
        )
