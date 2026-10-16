"""
Vanessa Cloud Server - High-Performance Remote AI & Omni-Platform Backend.
Runs on Dedicated VPS / Cloud GPU.
Features:
- High-concurrency FastAPI & WebSockets architecture
- Zero-latency bidirectional streaming with Victor's local thin desktop client
- OmniSync Hub: Real-time webhooks for WhatsApp, Discord, Telegram, Facebook/Meta
- Live game & music tracking (Steam Web API + Spotify Web API)
- 360° Digital Twin memory injection into Gemini 2.5 Flash / Pro
- Offloads 90% CPU/GPU/RAM from local computer to high-performance remote server
"""

import os
import sys
import json
import time
import asyncio
import logging
from typing import Set, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Query, Header, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.memory import MemoryManager
from core.system_control import SystemController
from core.file_manager import FileManager
from core.music_detector import MusicDetector
from core.brain import AssistantBrain
from core.omni_sync import OmniSyncHub
from core.user_auth import UserAuthDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VanessaCloudServer")

# Global instances
omni_hub: Optional[OmniSyncHub] = None
brain: Optional[AssistantBrain] = None
auth_db: Optional[UserAuthDB] = None
connected_clients: Set[WebSocket] = set()
background_poll_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global omni_hub, brain, auth_db, background_poll_task
    logger.info("Starting Vanessa Cloud Server & Omni-Platform Engine...")

    # 1. Initialize Authentication DB
    auth_db = UserAuthDB()

    # 2. Initialize Memory, System, and AssistantBrain
    memory = MemoryManager()
    sys_ctrl = SystemController()
    file_mgr = FileManager()
    music_det = MusicDetector()

    brain = AssistantBrain(
        memory=memory,
        sys_ctrl=sys_ctrl,
        file_mgr=file_mgr,
        music_det=music_det,
        personality_path="config/personality.json",
        settings_path="config/settings.json"
    )

    # 2. Initialize OmniSync Hub
    omni_hub = OmniSyncHub(config_path="config/cloud_config.json")

    # 3. Hook omni events to proactively notify connected desktop clients
    def on_omni_event(event_type: str, payload: Dict[str, Any]):
        asyncio.create_task(broadcast_to_clients({
            "type": "omni_notification",
            "event": event_type,
            "payload": payload,
            "timestamp": time.time()
        }))

    omni_hub.register_listener(on_omni_event)

    # 4. Start background polling loop for Steam & Spotify
    background_poll_task = asyncio.create_task(omni_hub.start_polling(interval_seconds=15))

    logger.info("Vanessa Cloud Engine fully armed & running.")
    yield

    logger.info("Shutting down Vanessa Cloud Server...")
    if omni_hub:
        omni_hub.stop_polling()
    if background_poll_task:
        background_poll_task.cancel()


app = FastAPI(
    title="Vanessa AI - High Performance Cloud Backend",
    version="2.0.0",
    description="Remote Brain & Multi-Platform OmniSync Hub for Vanessa Desktop Assistant",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_to_clients(data: Dict[str, Any]):
    """Sends a real-time event to all connected local desktop clients."""
    if not connected_clients:
        return
    msg = json.dumps(data)
    dead = set()
    for ws in list(connected_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)


# =============================================================================
# WEBSOCKET: THIN-CLIENT DESKTOP CONNECTION
# =============================================================================
@app.websocket("/ws/vanessa/client")
async def websocket_client_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    Main communication channel between local desktop (Vanessa thin client) and Cloud Server.
    Authenticates via token and streams speech, actions, expressions, and responses.
    """
    expected_token = omni_hub.config.get("server", {}).get("auth_token", "vanessa_secret")
    if token != expected_token:
        logger.warning(f"Rejected unauthorized WebSocket connection attempt (Invalid token: {token})")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Local desktop thin-client connected successfully! Total clients: {len(connected_clients)}")

    # Send welcome sync frame with current Digital Twin state
    await websocket.send_text(json.dumps({
        "type": "handshake_ok",
        "server_time": time.time(),
        "digital_twin": omni_hub.digital_twin,
        "message": "Vanessa Cloud Server enlazado. Carga computacional delegada al 100%."
    }))

    try:
        while True:
            text_data = await websocket.receive_text()
            try:
                msg = json.loads(text_data)
            except Exception:
                continue

            msg_type = msg.get("type")

            # A. Heartbeat / Ping
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "time": time.time()}))

            # B. User Voice / Text Prompt from Desktop Thin Client
            elif msg_type == "user_prompt":
                prompt_text = msg.get("prompt", "")
                client_context = msg.get("context", {})

                # 1. Inject real-time OmniSync Digital Twin context into prompt
                omni_context = omni_hub.get_digital_twin_prompt_context()

                # Augment prompt with rich context so Vanessa knows EVERYTHING in real time
                augmented_prompt = f"{prompt_text}\n\n[CONTEXTO DE SISTEMA OMNI-SYNC]\n{omni_context}"

                logger.info(f"Thinking on cloud for query: '{prompt_text[:60]}...'")

                # 2. Process query via Brain (Gemini 2.5 Flash / Pro + SQLite Memory)
                # Run asynchronously to avoid blocking event loop
                resp_text, emotion, action = await asyncio.to_thread(
                    brain.think,
                    prompt_text,
                    user_tone="friendly"
                )

                # 3. Stream response back to desktop thin client
                response_payload = {
                    "type": "vanessa_response",
                    "reply": resp_text,
                    "emotion": emotion or "relaxed",
                    "action": action or "idle",
                    "digital_twin_snapshot": {
                        "game": omni_hub.digital_twin["gaming"]["game_title"],
                        "track": omni_hub.digital_twin["music"]["track"],
                        "unread_social": omni_hub.digital_twin["social"]["unread_whatsapp"] + omni_hub.digital_twin["social"]["unread_discord_mentions"]
                    },
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(response_payload))

            # C. Screen / Vision perception update forwarded from desktop
            elif msg_type == "screen_update":
                app_title = msg.get("active_window", "")
                if app_title:
                    logger.debug(f"Desktop client active window: {app_title}")

    except WebSocketDisconnect:
        logger.info("Local desktop thin-client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket client error: {e}")
    finally:
        connected_clients.discard(websocket)


# =============================================================================
# WEBHOOKS: REAL-TIME SOCIAL & MESSAGING INGESTION
# =============================================================================

# 1. WHATSAPP CLOUD API WEBHOOK
@app.get("/api/v1/omni/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta verification challenge for WhatsApp Webhook registration."""
    expected = omni_hub.config.get("whatsapp", {}).get("verify_token", "")
    if hub_mode == "subscribe" and hub_verify_token == expected:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/api/v1/omni/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    """Receives live WhatsApp messages and notifications."""
    data = await request.json()
    extracted = omni_hub.handle_whatsapp_webhook(data)
    if extracted:
        logger.info(f"Ingested {len(extracted)} WhatsApp messages via Webhook.")
    return JSONResponse({"status": "received", "count": len(extracted)})


# 2. META / FACEBOOK MESSENGER & INSTAGRAM WEBHOOK
@app.get("/api/v1/omni/meta")
async def verify_meta_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    expected = omni_hub.config.get("meta", {}).get("verify_token", "")
    if hub_mode == "subscribe" and hub_verify_token == expected:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Meta verification token mismatch")


@app.post("/api/v1/omni/meta")
async def receive_meta_webhook(request: Request):
    data = await request.json()
    extracted = omni_hub.handle_meta_webhook(data)
    return JSONResponse({"status": "received", "count": len(extracted)})


# 3. TELEGRAM BOT WEBHOOK
@app.post("/api/v1/omni/telegram")
async def receive_telegram_webhook(request: Request):
    """Receives live updates and messages from Telegram Bot."""
    update = await request.json()
    item = omni_hub.handle_telegram_update(update)
    if item:
        logger.info(f"Ingested Telegram message from {item['sender']}: {item['content'][:50]}")
    return JSONResponse({"status": "ok"})


# 4. DISCORD EVENT INGESTION
@app.post("/api/v1/omni/discord/event")
async def receive_discord_event(request: Request):
    """Receives events forwarded from a dedicated Discord Gateway Bot."""
    data = await request.json()
    omni_hub.handle_discord_event(data)
    return JSONResponse({"status": "ok"})


# =============================================================================
# MONITORING & CONTROL ENDPOINTS
# =============================================================================
@app.get("/api/v1/omni/status")
async def get_omni_status():
    """Returns real-time status of all connected platforms and Digital Twin state."""
    return JSONResponse({
        "status": "online",
        "connected_desktop_clients": len(connected_clients),
        "digital_twin": omni_hub.digital_twin,
        "platform_integrations": {
            "whatsapp": omni_hub.config.get("whatsapp", {}).get("enabled", False),
            "discord": omni_hub.config.get("discord", {}).get("enabled", False),
            "telegram": omni_hub.config.get("telegram", {}).get("enabled", False),
            "meta_facebook": omni_hub.config.get("meta", {}).get("enabled", False),
            "steam": omni_hub.config.get("steam", {}).get("enabled", False),
            "spotify": omni_hub.config.get("spotify", {}).get("enabled", False)
        }
    })


@app.post("/api/v1/omni/sync_now")
async def trigger_immediate_sync():
    """Forces an immediate refresh of Steam and Spotify status."""
    await omni_hub.poll_steam_status()
    await omni_hub.poll_spotify_playback()
    return JSONResponse({
        "status": "synchronized",
        "digital_twin": omni_hub.digital_twin
    })


# =============================================================================
# USER AUTHENTICATION & LOGIN SYNCHRONIZATION ENDPOINTS
# =============================================================================
class AuthRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


@app.post("/api/v1/auth/register")
async def auth_register(req: AuthRequest):
    """Creates a user account and generates a sync session token."""
    global auth_db
    if not auth_db:
        auth_db = UserAuthDB()
    ok, msg, user_data = auth_db.register_user(req.email, req.password, req.display_name)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return JSONResponse({
        "status": "ok",
        "message": msg,
        "token": user_data["token"],
        "user": user_data
    })


@app.post("/api/v1/auth/login")
async def auth_login(req: AuthRequest):
    """Authenticates email + password and synchronizes all logins."""
    global auth_db
    if not auth_db:
        auth_db = UserAuthDB()
    ok, msg, user_data = auth_db.login_user(req.email, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return JSONResponse({
        "status": "ok",
        "message": msg,
        "token": user_data["token"],
        "user": user_data,
        "logins": user_data.get("logins", {})
    })


@app.get("/api/v1/auth/me")
async def auth_me(authorization: Optional[str] = Header(None)):
    """Returns profile and synchronized services for the authenticated user."""
    global auth_db
    if not auth_db:
        auth_db = UserAuthDB()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = authorization.split("Bearer ")[1].strip()
    session = auth_db.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Sesión expirada o inválida")
    return JSONResponse({"status": "ok", "user": session, "logins": session.get("logins", {})})


@app.post("/api/v1/auth/sync_all")
async def auth_sync_all(authorization: Optional[str] = Header(None)):
    """Refreshes synchronization for all logins (Steam, Spotify, Discord, etc.)."""
    global auth_db, omni_hub
    if not auth_db:
        auth_db = UserAuthDB()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = authorization.split("Bearer ")[1].strip()
    session = auth_db.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Sesión expirada o inválida")

    # Refresh service data in OmniHub if active
    if omni_hub:
        try:
            await omni_hub.poll_steam_status()
            await omni_hub.poll_spotify_playback()
        except Exception:
            pass

    logins = auth_db.sync_logins_for_user(session["user_id"])
    return JSONResponse({
        "status": "ok",
        "message": "Inicios de sesión sincronizados con la nube.",
        "logins": logins,
        "digital_twin": omni_hub.digital_twin if omni_hub else {}
    })


@app.post("/api/v1/auth/logout")
async def auth_logout(authorization: Optional[str] = Header(None)):
    global auth_db
    if not auth_db:
        auth_db = UserAuthDB()
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        auth_db.logout_token(token)
    return JSONResponse({"status": "ok", "message": "Sesión cerrada correctamente."})


if __name__ == "__main__":
    cfg = OmniSyncHub()._load_config()
    host = "0.0.0.0"
    port = int(cfg.get("server", {}).get("port", 8765))
    uvicorn.run("server_cloud:app", host=host, port=port, reload=False, workers=1)
