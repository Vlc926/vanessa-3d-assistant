"""
OmniSync Hub - Real-Time Multi-Platform Integration & Digital Twin Engine.
Aggregates live social media, messaging, and gaming APIs:
- WhatsApp (Cloud API Webhooks & message parsing)
- Discord (Bot Gateway / Webhooks / User Presence)
- Telegram (Bot API & Webhooks)
- Meta / Facebook (Graph API & Messenger Webhooks)
- Steam (Live Gaming Status, Playtime, Achievements)
- Spotify (Real-Time Playback, Audio Features, Mood)
- Google Calendar & Gmail (Schedule & Priority Inbox)

Maintains Victor's 360° Real-Time Profile ("Digital Twin") to feed Vanessa's Brain.
"""

import os
import json
import time
import asyncio
import logging
import aiohttp
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("OmniSync")
logger.setLevel(logging.INFO)


class OmniSyncHub:
    def __init__(self, config_path: str = "config/cloud_config.json"):
        self.config_path = config_path
        self.config = self._load_config()

        # Digital Twin - Victor's Live Context State
        self.digital_twin: Dict[str, Any] = {
            "last_updated": time.time(),
            "gaming": {
                "active": False,
                "game_title": None,
                "game_id": None,
                "session_minutes": 0,
                "recent_games": []
            },
            "music": {
                "active": False,
                "track": None,
                "artist": None,
                "album": None,
                "is_playing": False,
                "genre_vibe": "chill"
            },
            "social": {
                "unread_whatsapp": 0,
                "unread_telegram": 0,
                "unread_discord_mentions": 0,
                "unread_meta": 0,
                "latest_incoming_messages": []
            },
            "schedule": {
                "upcoming_events": [],
                "current_event": None
            },
            "emotional_state_estimate": "relaxed",
            "active_devices": ["Desktop Arch Linux"]
        }

        # Subscribers for live notifications (e.g. Vanessa brain)
        self.listeners: List[Callable[[str, Dict[str, Any]], None]] = []
        self._running = False
        self._poller_task: Optional[asyncio.Task] = None

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cloud_config.json: {e}")
        return {
            "server": {"port": 8765, "auth_token": "vanessa_secret_token_change_me"},
            "whatsapp": {"enabled": False, "phone_number_id": "", "access_token": "", "verify_token": ""},
            "discord": {"enabled": False, "bot_token": "", "client_id": ""},
            "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
            "meta": {"enabled": False, "access_token": "", "verify_token": "", "page_id": ""},
            "steam": {"enabled": False, "api_key": "", "steam_id": ""},
            "spotify": {"enabled": False, "client_id": "", "client_secret": "", "refresh_token": ""},
            "google": {"enabled": False, "calendar_id": "primary"}
        }

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def register_listener(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback for omni-channel events (e.g., incoming message, game launched)."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def emit_event(self, event_type: str, payload: Dict[str, Any]):
        for listener in self.listeners:
            try:
                listener(event_type, payload)
            except Exception as e:
                logger.error(f"Listener error on event {event_type}: {e}")

    # =========================================================================
    # 1. WHATSAPP CLOUD API & WEBHOOK INGESTION
    # =========================================================================
    def handle_whatsapp_webhook(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processes incoming WhatsApp Webhook payload from Meta Cloud API."""
        extracted = []
        try:
            entry = data.get("entry", [])
            for e in entry:
                for change in e.get("changes", []):
                    value = change.get("value", {})
                    contacts = {c.get("wa_id"): c.get("profile", {}).get("name", "Desconocido") for c in value.get("contacts", [])}
                    messages = value.get("messages", [])
                    for msg in messages:
                        from_id = msg.get("from")
                        sender_name = contacts.get(from_id, from_id)
                        msg_type = msg.get("type")
                        text = ""
                        if msg_type == "text":
                            text = msg.get("text", {}).get("body", "")
                        elif msg_type == "audio":
                            text = "[Nota de voz recibida]"
                        elif msg_type == "image":
                            text = f"[Imagen recibida: {msg.get('image', {}).get('caption', '')}]"

                        item = {
                            "source": "whatsapp",
                            "sender": sender_name,
                            "sender_id": from_id,
                            "timestamp": time.time(),
                            "content": text
                        }
                        extracted.append(item)
                        self._add_to_social_feed(item)
        except Exception as e:
            logger.error(f"Error handling WhatsApp webhook: {e}")
        return extracted

    async def send_whatsapp_message(self, recipient_phone: str, message: str) -> bool:
        """Sends WhatsApp message via Meta Cloud API."""
        cfg = self.config.get("whatsapp", {})
        if not cfg.get("enabled") or not cfg.get("access_token") or not cfg.get("phone_number_id"):
            logger.warning("WhatsApp API not configured")
            return False

        url = f"https://graph.facebook.com/v19.0/{cfg['phone_number_id']}/messages"
        headers = {
            "Authorization": f"Bearer {cfg['access_token']}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message}
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    return resp.status in (200, 201)
            except Exception as e:
                logger.error(f"WhatsApp send failed: {e}")
                return False

    # =========================================================================
    # 2. TELEGRAM BOT API & WEBHOOK
    # =========================================================================
    def handle_telegram_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes incoming Telegram message payload."""
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None

        sender = msg.get("from", {}).get("first_name", "Usuario")
        username = msg.get("from", {}).get("username", "")
        text = msg.get("text") or msg.get("caption") or "[Contenido multimedia]"

        item = {
            "source": "telegram",
            "sender": f"{sender} (@{username})" if username else sender,
            "sender_id": msg.get("chat", {}).get("id"),
            "timestamp": time.time(),
            "content": text
        }
        self._add_to_social_feed(item)
        return item

    async def send_telegram_message(self, chat_id: Optional[str], text: str) -> bool:
        cfg = self.config.get("telegram", {})
        token = cfg.get("bot_token")
        target_chat = chat_id or cfg.get("chat_id")
        if not token or not target_chat:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": target_chat, "text": text}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    return resp.status == 200
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                return False

    # =========================================================================
    # 3. DISCORD BOT / WEBHOOK / GATEWAY
    # =========================================================================
    def handle_discord_event(self, data: Dict[str, Any]):
        """Receives messages or notifications from Discord Bot Gateway."""
        item = {
            "source": "discord",
            "sender": data.get("author", "Discord User"),
            "channel": data.get("channel_name", "general"),
            "guild": data.get("guild_name", "Server"),
            "content": data.get("content", ""),
            "timestamp": time.time(),
            "is_mention": data.get("is_mention", False)
        }
        self._add_to_social_feed(item)
        if item["is_mention"]:
            self.digital_twin["social"]["unread_discord_mentions"] += 1
            self.emit_event("discord_mention", item)

    # =========================================================================
    # 4. META / FACEBOOK MESSENGER WEBHOOK
    # =========================================================================
    def handle_meta_webhook(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        extracted = []
        try:
            for entry in data.get("entry", []):
                for messaging in entry.get("messaging", []):
                    sender_id = messaging.get("sender", {}).get("id")
                    msg = messaging.get("message", {})
                    text = msg.get("text", "[Mensaje sin texto]")
                    item = {
                        "source": "meta_facebook",
                        "sender": f"Meta User ({sender_id})",
                        "sender_id": sender_id,
                        "timestamp": time.time(),
                        "content": text
                    }
                    extracted.append(item)
                    self._add_to_social_feed(item)
        except Exception as e:
            logger.error(f"Error handling Meta webhook: {e}")
        return extracted

    # =========================================================================
    # 5. STEAM GAMING API (Real-Time Play Status & Library Stats)
    # =========================================================================
    async def poll_steam_status(self):
        """Polls Steam Web API for Victor's current playing game and recent activity."""
        cfg = self.config.get("steam", {})
        if not cfg.get("enabled") or not cfg.get("api_key") or not cfg.get("steam_id"):
            return

        api_key = cfg["api_key"]
        steam_id = cfg["steam_id"]

        # Get Player Summary (live status & current game)
        url_summary = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={steam_id}"
        # Get Recently Played Games
        url_recent = f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/?key={api_key}&steamid={steam_id}&format=json"

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Check live status
                async with session.get(url_summary, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        players = data.get("response", {}).get("players", [])
                        if players:
                            p = players[0]
                            game_title = p.get("gameextrainfo")
                            game_id = p.get("gameid")
                            prev_game = self.digital_twin["gaming"]["game_title"]

                            if game_title:
                                self.digital_twin["gaming"]["active"] = True
                                self.digital_twin["gaming"]["game_title"] = game_title
                                self.digital_twin["gaming"]["game_id"] = game_id

                                if prev_game != game_title:
                                    logger.info(f"Steam: Victor started playing {game_title}")
                                    self.emit_event("game_started", {
                                        "game": game_title,
                                        "game_id": game_id
                                    })
                            else:
                                if self.digital_twin["gaming"]["active"]:
                                    self.emit_event("game_stopped", {"game": prev_game})
                                self.digital_twin["gaming"]["active"] = False
                                self.digital_twin["gaming"]["game_title"] = None

                # 2. Check recent library activity
                async with session.get(url_recent, timeout=5) as resp:
                    if resp.status == 200:
                        rec_data = await resp.json()
                        games = rec_data.get("response", {}).get("games", [])
                        self.digital_twin["gaming"]["recent_games"] = [
                            {"name": g.get("name"), "playtime_2weeks_hrs": round(g.get("playtime_2weeks", 0) / 60, 1)}
                            for g in games[:5]
                        ]
            except Exception as e:
                logger.debug(f"Steam poll error: {e}")

    # =========================================================================
    # 6. SPOTIFY MUSIC & MOOD API (Real-Time Playback)
    # =========================================================================
    async def poll_spotify_playback(self):
        """Polls Spotify Web API for current track and listening context."""
        cfg = self.config.get("spotify", {})
        if not cfg.get("enabled") or not cfg.get("refresh_token"):
            return

        token = await self._get_spotify_access_token()
        if not token:
            return

        url = "https://api.spotify.com/v1/me/player/currently-playing"
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        item = data.get("item")
                        is_playing = data.get("is_playing", False)
                        if item and is_playing:
                            track_name = item.get("name")
                            artists = ", ".join([a.get("name") for a in item.get("artists", [])])
                            album = item.get("album", {}).get("name")
                            prev_track = self.digital_twin["music"]["track"]

                            self.digital_twin["music"] = {
                                "active": True,
                                "track": track_name,
                                "artist": artists,
                                "album": album,
                                "is_playing": True,
                                "genre_vibe": self._estimate_music_vibe(track_name)
                            }

                            if prev_track != track_name:
                                self.emit_event("music_changed", self.digital_twin["music"])
                        else:
                            self.digital_twin["music"]["is_playing"] = False
                    elif resp.status == 204:
                        self.digital_twin["music"]["is_playing"] = False
            except Exception as e:
                logger.debug(f"Spotify poll error: {e}")

    async def _get_spotify_access_token(self) -> Optional[str]:
        cfg = self.config.get("spotify", {})
        client_id = cfg.get("client_id")
        client_secret = cfg.get("client_secret")
        refresh_token = cfg.get("refresh_token")

        if not (client_id and client_secret and refresh_token):
            return None

        # Check cached token
        cached = cfg.get("_cached_token")
        exp = cfg.get("_token_expiry", 0)
        if cached and time.time() < exp - 60:
            return cached

        url = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=payload) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        token = res.get("access_token")
                        expires_in = res.get("expires_in", 3600)
                        cfg["_cached_token"] = token
                        cfg["_token_expiry"] = time.time() + expires_in
                        return token
            except Exception as e:
                logger.error(f"Spotify token refresh error: {e}")
        return None

    def _estimate_music_vibe(self, track_title: str) -> str:
        t_low = (track_title or "").lower()
        if any(w in t_low for w in ["synthwave", "cyber", "phonk", "metal", "rock", "hard"]):
            return "energetic / focused"
        if any(w in t_low for w in ["lofi", "chill", "piano", "acoustic", "ambient", "sleep"]):
            return "relaxed / study"
        if any(w in t_low for w in ["anime", "opening", "ost", "jpop"]):
            return "happy / anime hype"
        return "casual listening"

    # =========================================================================
    # 7. DIGITAL TWIN CONTEXT GENERATOR FOR VANESSA'S LLM PROMPT
    # =========================================================================
    def _add_to_social_feed(self, item: Dict[str, Any]):
        feed = self.digital_twin["social"]["latest_incoming_messages"]
        feed.insert(0, item)
        if len(feed) > 15:
            feed.pop()
        self.digital_twin["last_updated"] = time.time()
        self.emit_event("social_message_received", item)

    def get_digital_twin_prompt_context(self) -> str:
        """
        Generates a rich, real-time contextual snapshot of Victor to be injected
        into Vanessa's LLM prompt, making her fully aware of his status, games,
        social messages, and activities.
        """
        lines = ["=== ESTADO Y PERFIL EN TIEMPO REAL DEL AMO VÍCTOR (OMNI-SYNC DIGITAL TWIN) ==="]

        # Gaming context
        gaming = self.digital_twin["gaming"]
        if gaming.get("active") and gaming.get("game_title"):
            lines.append(f"• ESTÁ JUGANDO AHORA MISMO: '{gaming['game_title']}' en Steam.")
        elif gaming.get("recent_games"):
            recent_str = ", ".join([f"{g['name']} ({g['playtime_2weeks_hrs']}h rec.)" for g in gaming["recent_games"][:3]])
            lines.append(f"• Juegos recientes en Steam: {recent_str}")

        # Music context
        music = self.digital_twin["music"]
        if music.get("is_playing") and music.get("track"):
            lines.append(f"• ESCUCHANDO EN SPOTIFY: '{music['track']}' de {music['artist']} (Vibra: {music['genre_vibe']}).")

        # Social messages context
        social = self.digital_twin["social"]
        msgs = social.get("latest_incoming_messages", [])
        if msgs:
            lines.append("• ÚLTIMOS MENSAJES Y NOTIFICACIONES RECIBIDAS (Redes & Mensajería):")
            for m in msgs[:4]:
                src = m.get("source", "").upper()
                sender = m.get("sender", "Alguien")
                content = m.get("content", "")[:90]
                lines.append(f"   [{src}] {sender}: \"{content}\"")

        # Schedule
        sched = self.digital_twin["schedule"]
        if sched.get("upcoming_events"):
            lines.append(f"• Próximo compromiso en agenda: {sched['upcoming_events'][0]}")

        lines.append("=============================================================================")
        return "\n".join(lines)

    # =========================================================================
    # 8. BACKGROUND POLLING LOOP
    # =========================================================================
    async def start_polling(self, interval_seconds: int = 20):
        self._running = True
        logger.info("OmniSync Hub background polling started...")
        while self._running:
            try:
                # Concurrent polling for non-webhook APIs
                await asyncio.gather(
                    self.poll_steam_status(),
                    self.poll_spotify_playback(),
                    return_exceptions=True
                )
            except Exception as e:
                logger.error(f"Error in OmniSync poll cycle: {e}")
            await asyncio.sleep(interval_seconds)

    def stop_polling(self):
        self._running = False
