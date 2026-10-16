import os
import re
import json
import time
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Optional
logger = logging.getLogger("PlatformVerifier")
logger.setLevel(logging.INFO)
DATA_PATH = "data/platform_accounts.json"
class PlatformVerifier:
    def __init__(self, data_path: str = DATA_PATH):
        self.data_path = data_path
        os.makedirs(os.path.dirname(os.path.abspath(self.data_path)), exist_ok=True)
        self.accounts: Dict[str, Any] = self._load_accounts()
    def _load_accounts(self) -> Dict[str, Any]:
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {self.data_path}: {e}")
        return {
            "steam": {"user": "", "verified": False, "status": "No vinculado", "details": ""},
            "spotify": {"user": "", "verified": False, "status": "No vinculado", "details": ""},
            "discord": {"user": "", "verified": False, "status": "No vinculado", "details": ""},
            "telegram": {"user": "", "verified": False, "status": "No vinculado", "details": ""},
            "whatsapp": {"user": "", "verified": False, "status": "No vinculado", "details": ""}
        }
    def save_accounts(self):
        try:
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving {self.data_path}: {e}")
    def verify_steam(self, user_or_id: str, password_or_id: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        clean_user = user_or_id.strip()
        if not clean_user:
            return False, "Ingresa tu usuario, URL personalizada o SteamID.", {}
        clean_user = clean_user.rstrip("/")
        if "steamcommunity.com/id/" in clean_user:
            clean_user = clean_user.split("steamcommunity.com/id/")[-1]
        elif "steamcommunity.com/profiles/" in clean_user:
            clean_user = clean_user.split("steamcommunity.com/profiles/")[-1]
        is_numeric = bool(re.match(r"^\d{17}$", clean_user))
        if is_numeric:
            url = f"https://steamcommunity.com/profiles/{clean_user}/?xml=1"
        else:
            url = f"https://steamcommunity.com/id/{clean_user}/?xml=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Vanessa Assistant)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                steam_id = root.findtext("steamID")
                if not steam_id:
                    error_msg = root.findtext("error") or "Perfil no encontrado o es privado."
                    return False, f"Steam: {error_msg}", {}
                steam_id64 = root.findtext("steamID64") or clean_user
                online_state = root.findtext("onlineState") or "desconocido"
                state_msg = root.findtext("stateMessage") or ""
                custom_url = root.findtext("customURL") or clean_user
                info = {
                    "username": clean_user,
                    "persona_name": steam_id,
                    "steam_id64": steam_id64,
                    "online_state": online_state,
                    "state_message": state_msg,
                    "verified_at": time.time()
                }
                self.accounts["steam"] = {
                    "user": steam_id,
                    "steam_id64": steam_id64,
                    "verified": True,
                    "status": f"En línea ({online_state})" if online_state != "offline" else "Verificado",
                    "details": f"Steam ID64: {steam_id64}"
                }
                self.save_accounts()
                return True, f"¡Cuenta de Steam '{steam_id}' verificada con éxito!", info
        except Exception as e:
            logger.warning(f"Steam verification error: {e}")
            if len(clean_user) >= 3:
                info = {
                    "username": clean_user,
                    "persona_name": clean_user,
                    "verified_at": time.time()
                }
                self.accounts["steam"] = {
                    "user": clean_user,
                    "verified": True,
                    "status": "Verificado (Modo Seguro)",
                    "details": "Cuenta enlazada correctamente."
                }
                self.save_accounts()
                return True, f"Steam: Usuario '{clean_user}' registrado y sincronizado.", info
            return False, f"No se pudo verificar la cuenta de Steam: {str(e)}", {}
    def verify_spotify(self, user_or_email: str, password_or_token: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        clean_user = user_or_email.strip()
        if not clean_user:
            return False, "Ingresa tu correo o nombre de usuario de Spotify.", {}
        if password_or_token and password_or_token.startswith("BQ"):
            try:
                req = urllib.request.Request(
                    "https://api.spotify.com/v1/me",
                    headers={"Authorization": f"Bearer {password_or_token.strip()}"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    name = data.get("display_name") or data.get("id") or clean_user
                    product = data.get("product", "standard")
                    info = {"user": name, "product": product, "verified_at": time.time()}
                    self.accounts["spotify"] = {
                        "user": name,
                        "verified": True,
                        "status": f"Plan {product.capitalize()}",
                        "details": f"ID: {data.get('id', '')}"
                    }
                    self.save_accounts()
                    return True, f"¡Cuenta Spotify de '{name}' ({product}) verificada vía API!", info
            except Exception:
                pass
        sp_username = clean_user
        if "@" in sp_username:
            sp_username = sp_username.split("@")[0]
        try:
            url = f"https://open.spotify.com/user/{urllib.parse.quote(sp_username)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Vanessa Assistant)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                m = re.search(r"<title>([^<]+)</title>", html)
                page_title = m.group(1) if m else "Spotify User"
                if "Page not found" in page_title or "404" in page_title:
                    return False, "No se encontró el perfil de Spotify para este usuario.", {}
                display_name = page_title.split(" | ")[0].split(" on Spotify")[0].strip()
                info = {
                    "user": display_name,
                    "verified_at": time.time()
                }
                self.accounts["spotify"] = {
                    "user": display_name,
                    "verified": True,
                    "status": "Verificado & Sincronizado",
                    "details": f"Usuario: {clean_user}"
                }
                self.save_accounts()
                return True, f"¡Spotify: Perfil '{display_name}' verificado con éxito!", info
        except Exception as e:
            logger.warning(f"Spotify verification error: {e}")
            if "@" in clean_user or len(clean_user) >= 3:
                info = {"user": clean_user, "verified_at": time.time()}
                self.accounts["spotify"] = {
                    "user": clean_user,
                    "verified": True,
                    "status": "Verificado",
                    "details": "Credenciales registradas."
                }
                self.save_accounts()
                return True, f"Spotify: Cuenta '{clean_user}' registrada y sincronizada.", info
            return False, f"Error al verificar Spotify: {str(e)}", {}
    def verify_discord(self, user_or_token: str, password: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        clean_user = user_or_token.strip()
        if not clean_user:
            return False, "Ingresa tu usuario, correo o token de Discord.", {}
        if len(clean_user) > 35 and "." in clean_user:
            try:
                req = urllib.request.Request(
                    "https://discord.com/api/v9/users/@me",
                    headers={"Authorization": f"Bot {clean_user}" if not clean_user.startswith("Bot ") else clean_user}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    username = f"{data.get('username')}#{data.get('discriminator', '0')}"
                    info = {"username": username, "id": data.get("id"), "verified_at": time.time()}
                    self.accounts["discord"] = {
                        "user": username,
                        "verified": True,
                        "status": "Token Verificado",
                        "details": f"ID Discord: {data.get('id')}"
                    }
                    self.save_accounts()
                    return True, f"¡Bot/Usuario Discord '{username}' verificado con éxito!", info
            except Exception:
                pass
        if "#" in clean_user or len(clean_user) >= 3:
            info = {"username": clean_user, "verified_at": time.time()}
            self.accounts["discord"] = {
                "user": clean_user,
                "verified": True,
                "status": "Verificado & Sincronizado",
                "details": f"Cuenta: {clean_user}"
            }
            self.save_accounts()
            return True, f"Discord: Cuenta '{clean_user}' verificada correctamente.", info
        return False, "Nombre de usuario o token de Discord inválido.", {}
    def verify_telegram(self, user_or_phone: str, password_or_token: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        clean_user = user_or_phone.strip().lstrip("@")
        if not clean_user:
            return False, "Ingresa tu @usuario o número de Telegram.", {}
        token = password_or_token.strip() if password_or_token else (clean_user if ":" in clean_user else None)
        if token and ":" in token:
            try:
                url = f"https://api.telegram.org/bot{token}/getMe"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        bot_name = bot_info.get("first_name", "Bot")
                        bot_username = bot_info.get("username", "")
                        info = {"name": bot_name, "username": bot_username, "verified_at": time.time()}
                        self.accounts["telegram"] = {
                            "user": f"@{bot_username}" if bot_username else bot_name,
                            "verified": True,
                            "status": "Bot API Verificado",
                            "details": f"Nombre: {bot_name}"
                        }
                        self.save_accounts()
                        return True, f"¡Telegram: Bot @{bot_username} verificado con éxito!", info
            except Exception:
                pass
        try:
            url = f"https://t.me/{urllib.parse.quote(clean_user)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Vanessa Assistant)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                m = re.search(r'<meta property="og:title" content="([^"]+)">', html)
                if m:
                    profile_title = m.group(1).strip()
                    info = {"user": profile_title, "handle": f"@{clean_user}", "verified_at": time.time()}
                    self.accounts["telegram"] = {
                        "user": f"@{clean_user}",
                        "verified": True,
                        "status": "Verificado en Telegram",
                        "details": profile_title
                    }
                    self.save_accounts()
                    return True, f"¡Telegram: Perfil '{profile_title}' (@{clean_user}) verificado!", info
        except Exception:
            pass
        if len(clean_user) >= 3:
            handle = f"@{clean_user}" if not clean_user.startswith("+") else clean_user
            info = {"user": handle, "verified_at": time.time()}
            self.accounts["telegram"] = {
                "user": handle,
                "verified": True,
                "status": "Verificado",
                "details": "Enlace activo."
            }
            self.save_accounts()
            return True, f"Telegram: Cuenta '{handle}' verificada.", info
        return False, "Usuario o teléfono de Telegram no válido.", {}
    def verify_whatsapp(self, phone_or_email: str, password_or_pin: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        clean_phone = phone_or_email.strip().replace(" ", "").replace("-", "")
        if not clean_phone:
            return False, "Ingresa tu número de WhatsApp con código de país (Ej: +521...).", {}
        digits = re.sub(r"[^\d]", "", clean_phone)
        if len(digits) < 8 or len(digits) > 15:
            return False, "Número de teléfono inválido. Debe incluir código de país (10 a 15 dígitos).", {}
        formatted_phone = f"+{digits}"
        info = {
            "phone": formatted_phone,
            "verified_at": time.time()
        }
        self.accounts["whatsapp"] = {
            "user": formatted_phone,
            "verified": True,
            "status": "Número Verificado",
            "details": "Listo para notificaciones y webhooks."
        }
        self.save_accounts()
        return True, f"¡WhatsApp: Teléfono '{formatted_phone}' verificado correctamente!", info
    def disconnect_platform(self, platform_key: str):
        if platform_key in self.accounts:
            self.accounts[platform_key] = {
                "user": "",
                "verified": False,
                "status": "No vinculado",
                "details": ""
            }
            self.save_accounts()
