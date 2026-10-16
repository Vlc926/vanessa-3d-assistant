"""
App Connectors Skill for Vanessa.
Provides seamless integration with Victor's core daily tools:
- WhatsApp (Web / Desktop direct messaging, URL schema with prefilled text)
- Discord (Webhooks, Channel switching, App opening)
- Gmail (Instant compose links with prefilled recipient, subject, and body)
- YouTube (Direct media search, playlist launch, background audio)
- Desktop App Switcher (Hyprland window focus and launching)
"""
import os
import urllib.parse
import subprocess
import webbrowser
from typing import Dict, Any, Optional


class AppConnectors:
    def __init__(self):
        pass

    def open_whatsapp(self, phone: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
        """Opens WhatsApp Web or Desktop with optional recipient and prefilled message."""
        if phone or message:
            clean_phone = "".join(c for c in (phone or "") if c.isdigit() or c == "+")
            params = {}
            if clean_phone:
                params["phone"] = clean_phone
            if message:
                params["text"] = message
            qs = urllib.parse.urlencode(params)
            url = f"https://web.whatsapp.com/send?{qs}"
        else:
            url = "https://web.whatsapp.com"

        webbrowser.open(url)
        return {"app": "WhatsApp", "status": "opened", "url": url}

    def open_gmail_compose(self, to: str = "", subject: str = "", body: str = "") -> Dict[str, Any]:
        """Opens Gmail Compose window in browser with pre-filled recipient, subject, and body."""
        params = {
            "view": "cm",
            "fs": "1"
        }
        if to:
            params["to"] = to
        if subject:
            params["su"] = subject
        if body:
            params["body"] = body

        qs = urllib.parse.urlencode(params)
        url = f"https://mail.google.com/mail/?{qs}"
        webbrowser.open(url)
        return {"app": "Gmail", "status": "compose_opened", "to": to, "subject": subject}

    def open_discord(self, guild_id: Optional[str] = None, channel_id: Optional[str] = None) -> Dict[str, Any]:
        """Opens Discord desktop client or web version at specific channel."""
        # Check if desktop client is installed
        try:
            # First attempt: hyprland focus or launch discord
            res = subprocess.run(["hyprctl", "dispatch", "focuswindow", "class:discord"], capture_output=True, text=True)
            if "ok" in res.stdout.lower():
                return {"app": "Discord", "status": "focused"}
        except Exception:
            pass

        if guild_id and channel_id:
            url = f"https://discord.com/channels/{guild_id}/{channel_id}"
        else:
            url = "https://discord.com/channels/@me"

        webbrowser.open(url)
        return {"app": "Discord", "status": "opened", "url": url}

    def search_youtube(self, query: str) -> Dict[str, Any]:
        """Opens YouTube search results in Victor's browser."""
        safe_q = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={safe_q}"
        webbrowser.open(url)
        return {"app": "YouTube", "status": "searching", "query": query, "url": url}

    def focus_or_launch(self, app_name: str) -> Dict[str, Any]:
        """Intelligently focuses an existing window or launches the application via Hyprland."""
        app_lower = app_name.lower().strip()
        app_map = {
            "terminal": "kitty",
            "kitty": "kitty",
            "neovim": "nvim",
            "nvim": "kitty -e nvim",
            "vscode": "code",
            "code": "code",
            "spotify": "spotify",
            "telegram": "telegram-desktop",
            "navegador": "brave",
            "chrome": "google-chrome-stable",
            "firefox": "firefox"
        }

        cmd = app_map.get(app_lower, app_lower)

        # Attempt to focus first if already running
        try:
            res = subprocess.run(["hyprctl", "dispatch", "focuswindow", f"class:{cmd}"], capture_output=True, text=True)
            if "ok" in res.stdout.lower():
                return {"app": cmd, "status": "focused"}
        except Exception:
            pass

        # Otherwise launch
        try:
            subprocess.Popen(cmd.split())
            return {"app": cmd, "status": "launched"}
        except Exception as e:
            return {"app": cmd, "status": "error", "error": str(e)}
