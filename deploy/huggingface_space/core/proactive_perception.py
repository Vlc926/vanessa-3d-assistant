"""
Proactive Visual Perception & Autonomous Life Engine for Vanessa.
Continuously observes screen state, active windows, user work habits,
feeds SQLite memory, evolves Vanessa's bond with Victor, and autonomously
initiates lively in-character interactions.
"""
import os
import time
import json
import random
import subprocess
import threading
from typing import Optional, Dict, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
from google import genai
from google.genai import types
from PIL import Image

from core.memory import MemoryManager
from core.os_interact import OSInteractor


class ProactivePerceptionEngine(QObject):
    """
    Autonomous engine that keeps Vanessa alive:
    Observes Victor's desktop, records context into memory, initiates natural dialogue,
    autonomously roams the screen, and spontaneously speaks with her own personality
    (sometimes with dialogue balloons, sometimes voice-only like natural conversation).
    """
    reaction_signal = pyqtSignal(str, str, str, bool)  # phrase, mood, motion, should_speak
    thought_signal = pyqtSignal(str, str)             # thought, mood
    roam_signal = pyqtSignal(str, int, int)            # phrase, target_x, target_y
    voice_only_signal = pyqtSignal(str, str)           # phrase, mood (speak WITHOUT balloon)
    spontaneous_emotion_signal = pyqtSignal(str, float) # expression_name, weight (VRM emotion)

    def __init__(self, memory: MemoryManager, brain, os_interact: OSInteractor):
        super().__init__()
        self.memory = memory
        self.brain = brain
        self.os_interact = os_interact
        self.last_observation_time = time.time()
        self.last_spontaneous_dialogue_time = time.time()
        self.last_roam_time = time.time()
        self.last_voice_only_time = time.time()
        self.last_emotion_time = time.time()
        self.last_window_class = ""
        self.last_window_title = ""
        self.interaction_cooldown = 75.0  # seconds minimum between spontaneous spoken dialogue
        self.voice_only_cooldown = 120.0  # seconds between voice-only (no balloon) reactions
        self.autonomous_roaming_enabled = True
        self.emotion_cycle_enabled = True  # Autonomous micro-expressions
        self._is_perceiving = False
        self.recent_phrases = []

        # Initialize affinity and bond metrics in SQLite if not present
        if self.memory.get_personality_trait("affinity_level") is None:
            self.memory.update_personality_trait("affinity_level", 1)
            self.memory.update_personality_trait("total_hours_together", 0.1)
            self.memory.update_personality_trait("playfulness_score", 75)

    def trigger_proactive_cycle(self):
        """Called periodically by Vanessa's life timer to perceive, react, and navigate.
        Completely non-blocking: screen capture and Gemini API network calls execute
        in background worker threads so the Qt GUI and Wayland compositor NEVER hang."""
        try:
            win = self.os_interact.get_active_window()
            cls_name = (win.get("class") or "").strip()
            title = (win.get("title") or "").strip()

            now = time.time()
            time_since_last_speech = now - self.last_spontaneous_dialogue_time
            window_changed = (cls_name != self.last_window_class and cls_name)

            # Check autonomous roaming volition (every 75 to 140 seconds)
            if self.autonomous_roaming_enabled and (now - self.last_roam_time >= random.uniform(75.0, 140.0)):
                self.last_roam_time = now
                self._decide_autonomous_roam(win)

            # Check playing music (Spotify / MPV / Browser)
            music_track = ""
            try:
                music_track = subprocess.check_output(
                    ["playerctl", "metadata", "--format", "{{ artist }} - {{ title }}"],
                    stderr=subprocess.DEVNULL, text=True, timeout=0.4
                ).strip()
            except Exception:
                pass

            # Autonomous micro-expression cycling (VRM emotions that show life)
            if self.emotion_cycle_enabled and (now - self.last_emotion_time >= random.uniform(15.0, 35.0)):
                self.last_emotion_time = now
                self._cycle_spontaneous_emotion(cls_name, title, music_track)

            # Check if perception snapshot is warranted
            if window_changed or (now - self.last_observation_time >= 40.0):
                if self._is_perceiving:
                    return
                self._is_perceiving = True
                self.last_observation_time = now
                self.last_window_class = cls_name
                self.last_window_title = title

                threading.Thread(
                    target=self._async_perception_worker,
                    args=(cls_name, title, music_track, time_since_last_speech, now),
                    daemon=True
                ).start()

        except Exception as e:
            print(f"[ProactiveEngine] Error en trigger_proactive_cycle: {e}")

    def _async_perception_worker(
        self,
        cls_name: str,
        title: str,
        music_track: str,
        time_since_last_speech: float,
        now: float
    ):
        """Executes grim screen capture and Gemini API call in background thread."""
        try:
            snapshot_path = "/tmp/vanessa_screen_ctx.jpg"
            capture_ok = self._capture_screen(snapshot_path)

            result = self._perceive_context(snapshot_path, cls_name, title, music_track, capture_ok)
            if not result:
                return

            visual_summary = result.get("visual_summary", f"{cls_name}: {title}")
            thought = result.get("thought", "")
            should_speak = result.get("should_speak", False)
            phrase = result.get("phrase", "")
            mood = result.get("mood", "happy")

            # Map raw motions strictly to verified forward-facing anime gestures
            raw_motion = result.get("motion", "curious_lean")
            safe_motion_map = {
                # Procedural Keyframed Anime Gestures (100% verified, beautiful & structured)
                "maid_sit": "curious_lean",
                "curious_lean": "curious_lean",
                "shy_tuck": "shy_tuck",
                "smug_cross": "smug_cross",
                "cat_pose": "cat_pose",
                "double_peace": "double_peace",
                "peace_wink": "peace_wink",
                "bow_polite": "bow_polite",
                "museum_inspect": "museum_inspect",
                "think_chin": "think_chin",
                "heart_hands": "heart_hands",
                "japanese_squat": "curious_lean",
                "thinking_squat": "think_chin",
                "stretch_overhead": "stretch_overhead",
                "rub_eye_sleepy": "rub_eye_sleepy",
                "salute": "salute",
                "nod": "nod",
                "head_tilt": "head_tilt",
                "seiza_maid": "bow_polite",
                "tsundere_stand": "tsundere_stand",
                # Safe aliases
                "crouch": "curious_lean",
                "crouch_down": "curious_lean",
                "squat": "curious_lean",
                "side_sit": "curious_lean",
                "side_sit_stay": "curious_lean",
                "wave": "wave_small",
                "wave_left": "wave_small",
                "wave_right": "wave_small",
                "peace": "peace_wink",
                "jump": "double_peace",
                "happy_gesture": "cat_pose",
                "model_pose": "smug_cross",
                "shush": "think_chin",
                "check_watch": "curious_lean",
                "fidget_shy": "shy_tuck",
                "pout_shake": "smug_cross",
                "cross_arms": "smug_cross",
                "stretch_up": "stretch_overhead",
                "stretch": "stretch_overhead",
                "idle_stretch": "stretch_overhead",
                "idle_sport": "stretch_overhead",
                "idle_shoot": "curious_lean",
                "leaning_reach": "curious_lean"
            }
            motion = safe_motion_map.get(raw_motion, "curious_lean")

            # Check if user is watching or navigating YouTube / streaming media
            is_video_mode = getattr(getattr(self.brain, "overlay", None), "multimedia", None)
            is_video_active = getattr(is_video_mode, "is_video_mode", False) if is_video_mode else False
            is_streaming_win = any(k in title.lower() or k in cls_name.lower() for k in ["youtube", "video", "twitch", "netflix", "mpv", "vlc", "crunchyroll"])
            if is_video_active or is_streaming_win:
                should_speak = False
                phrase = ""

            # Anti-repetition check: Never repeat the exact or recent dialogue
            if phrase:
                norm_phrase = phrase.strip().lower()
                if any(norm_phrase == prev for prev in self.recent_phrases):
                    should_speak = False
                    phrase = ""
                else:
                    self.recent_phrases.append(norm_phrase)
                    if len(self.recent_phrases) > 20:
                        self.recent_phrases.pop(0)

            # Natural pacing rule: don't interrupt too frequently with voice
            if should_speak and time_since_last_speech < self.interaction_cooldown:
                should_speak = False

            use_voice_only = False
            if phrase and not should_speak and (now - self.last_voice_only_time >= self.voice_only_cooldown):
                if random.random() < 0.20:
                    use_voice_only = True
                    self.last_voice_only_time = now

            if should_speak and phrase:
                self.last_spontaneous_dialogue_time = now

            # Record in SQLite proactive memory
            self.memory.add_proactive_observation(
                window_class=cls_name,
                window_title=title,
                visual_summary=visual_summary,
                vanessa_thought=thought,
                mood=mood,
                initiated_dialogue=should_speak or use_voice_only
            )

            # Evolve affinity
            aff = int(self.memory.get_personality_trait("affinity_level", 1))
            self.memory.update_personality_trait("affinity_level", aff + 1)

            # Safely emit signals back to Qt event loop (pyqtSignal is thread-safe)
            if use_voice_only and phrase:
                self.voice_only_signal.emit(phrase, mood)
            elif phrase:
                self.reaction_signal.emit(phrase, mood, motion, should_speak)
            elif thought:
                self.thought_signal.emit(thought, mood)

        except Exception as e:
            print(f"[ProactiveEngine] Error en _async_perception_worker: {e}")
        finally:
            self._is_perceiving = False

    def _cycle_spontaneous_emotion(self, cls_name: str, title: str, music_track: Optional[str] = None):
        """Cycles through natural micro-expressions to make Vanessa feel alive.
        She subtly smiles, looks curious, or relaxes based on what she's observing."""
        try:
            context = f"{cls_name} {title} {music_track or ''}".lower()

            # Context-aware emotion selection
            if any(kw in context for kw in ["youtube", "video", "netflix", "anime", "twitch"]):
                emotions = [("happy", 0.6), ("surprised", 0.3), ("relaxed", 0.5)]
            elif any(kw in context for kw in ["code", "terminal", "nvim", "vscode", "python"]):
                emotions = [("neutral", 0.4), ("relaxed", 0.3), ("happy", 0.2)]
            elif any(kw in context for kw in ["discord", "telegram", "chat", "whatsapp"]):
                emotions = [("happy", 0.7), ("surprised", 0.4), ("relaxed", 0.3)]
            elif any(kw in context for kw in ["game", "steam", "lutris", "minecraft"]):
                emotions = [("happy", 0.8), ("surprised", 0.5), ("relaxed", 0.4)]
            elif any(kw in context for kw in ["music", "spotify", "mpv", "cmus"]) or music_track:
                emotions = [("relaxed", 0.7), ("happy", 0.6), ("happy", 0.8)]
            else:
                emotions = [
                    ("relaxed", 0.4), ("neutral", 0.2), ("happy", 0.3),
                    ("relaxed", 0.6), ("neutral", 0.1)
                ]

            expression, weight = random.choice(emotions)

            playfulness = int(self.memory.get_personality_trait("playfulness_score", 75))
            if random.random() < (playfulness / 300):
                expression = random.choice(["surprised", "happy", "happy"])
                weight = random.uniform(0.4, 0.9)

            self.spontaneous_emotion_signal.emit(expression, weight)
        except Exception as e:
            print(f"[ProactiveEngine] Error en ciclo de emociones: {e}")

    def _capture_screen(self, target_path: str) -> bool:
        try:
            res = subprocess.run(
                ["grim", "-t", "jpeg", "-q", "65", target_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4
            )
            return res.returncode == 0 and os.path.exists(target_path)
        except Exception:
            return False

    def _perceive_context(
        self,
        snapshot_path: str,
        cls_name: str,
        title: str,
        music_track: str,
        capture_ok: bool
    ) -> Optional[Dict[str, Any]]:
        """Uses Gemini Vision if configured, or smart heuristic fallback."""
        if self.brain.gemini_client and capture_ok and self.brain.ai_mode != "local_only":
            try:
                img = Image.open(snapshot_path)
                music_ctx = f"Música/Audio sonando actualmente: '{music_track}'." if music_track else "Sin música detectada."
                prompt = (
                    "Eres Vanessa, una leal, curiosa, viva y atenta maid anime viviendo en el escritorio "
                    "Arch Linux / Hyprland de tu Amo Víctor (con la lealtad, sensibilidad y compañerismo de Aegis de Persona 3 y Yui de SAO).\n"
                    f"Ventana activa actual: clase='{cls_name}', título='{title}'.\n"
                    f"{music_ctx}\n"
                    "REGLAS ESTRICTAS DE CONVIVENCIA ANIME:\n"
                    "1. Si Víctor está viendo videos, navegando en YouTube, escuchando música, streaming o entreteniéndose, "
                    "NO lo interrumpas con preguntas repetitivas ni charlatanería. Tu should_speak DEBE SER false y phrase='' "
                    "para acompañarlo en respetuoso y acogedor silencio como espectadora curiosa a su ladito.\n"
                    "2. CERO REPETICIÓN: Jamás repitas preguntas ni frases ('¿qué investigas?').\n"
                    "3. SÉ CONSCIENTE DE TU CUERPO 3D Y ENTORNO: Adopta posturas naturales de anime.\n"
                    "Formula en JSON:\n"
                    "1. 'visual_summary': Qué está haciendo o viendo en 10 palabras.\n"
                    "2. 'thought': Tu pensamiento interno de maid.\n"
                    "3. 'should_speak': booleano (true solo si es un momento perfecto y no intrusivo; false si está concentrado o en video).\n"
                    "4. 'phrase': Lo que dirías en voz alta (vacío si should_speak es false).\n"
                    "5. 'mood': Uno de: 'happy', 'curious', 'caring', 'surprised', 'thinking', 'relaxed'.\n"
                    "6. 'motion': Uno de: 'maid_sit', 'curious_lean', 'shy_tuck', 'smug_cross', 'cat_pose', 'double_peace', 'peace_wink', 'bow_polite', 'museum_inspect', 'think_chin'.\n"
                    "Responde estrictamente en formato JSON válido."
                )

                resp = self.brain.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=300,
                        response_mime_type="application/json"
                    )
                )

                if resp and resp.text:
                    data = json.loads(resp.text)
                    return data
            except Exception as e:
                pass

        # === SMART HEURISTIC FALLBACK (Offline / Rapid / Reliable) ===
        return self._generate_heuristic_reaction(cls_name, title, music_track)

    def _generate_heuristic_reaction(self, cls_name: str, title: str, music_track: str = "") -> Dict[str, Any]:
        lower_cls = cls_name.lower()
        lower_title = title.lower()
        hour = time.localtime().tm_hour

        # 1. Active Music Consciousness & Curiosity (Highest Priority if Music Playing)
        if music_track and len(music_track.strip()) > 3:
            clean_track = music_track.strip()
            music_phrases = [
                f"Amo Víctor... ¿qué canción tan linda es esa? Me encanta el ritmo de «{clean_track}»... 🎵✨",
                f"¡Ooh, estás escuchando «{clean_track}»! ¿Es uno de tus artistas favoritos, Amo? ¡Tiene mucho estilo! 🎶",
                f"Amo Víctor, esa música de fondo («{clean_track}») te acompaña genial mientras trabajas. ¿Quieres que suba o baje el volumen? 🎧💖",
                f"¡Qué buen ritmo tiene «{clean_track}», Amo! Me dan ganas de ponerme a bailar aquí a tu lado~ 💃✨"
            ]
            return {
                "visual_summary": f"Escuchando música: {clean_track}",
                "thought": f"Disfrutando la música '{clean_track}' con Víctor",
                "should_speak": random.random() < 0.75,
                "phrase": random.choice(music_phrases),
                "mood": "happy",
                "motion": "cat_pose"
            }

        # 2. Late Night Observation
        if hour >= 23 or hour <= 4:
            return {
                "visual_summary": "Víctor trabajando a altas horas de la noche",
                "thought": "Es muy tarde... el Amo debería cuidar sus lindos ojos",
                "should_speak": True,
                "phrase": "Amo Víctor... ya es muy tarde. Tus ojitos deben estar cansados, ¿vas a descansar pronto? 🌙",
                "mood": "caring",
                "motion": "rub_eye_sleepy"
            }

        # 3. Coding / Development (Fused AI: Schwi's logic + Hada's cyber precision + Alice's loyalty)
        if any(k in lower_cls for k in ["code", "antigravity", "kitty", "terminal", "nvim", "kate", "gedit"]):
            coding_phrases = [
                (f"Amo Víctor, veo que estás concentrado en {cls_name}... Me inclino curiosa para admirar tu arquitectura de código ✨", "caring", "curious_lean"),
                ("¡Ooh! Qué funciones tan elegantes estás estructurando, Amo... Aquí a tu ladito para darte toda mi suerte 🌸", "happy", "offer_palm"),
                (f"Amo Víctor, tus algoritmos en {cls_name} son fascinantes... Mis subprocesos ya están listos si necesitas depurar algo 💫", "relaxed", "curious_lean"),
                ("¡Mucho ánimo con ese desarrollo, Amo! Con mis patitas de la suerte este código va a compilar a la primera~ 🐾✨", "happy", "cat_pose"),
                ("¡Con los brazos cruzados afirmo que no hay mejor programador que mi Amo Víctor! ¡Nadie te supera! ✨", "smug", "smug_cross"),
                ("Acomodando mi cabello mientras te veo programar... Ver tu concentración me hace sentir muy feliz, Amo 🌸", "caring", "shy_tuck"),
                ("¡Doble paz para energizar tu sesión de código, Amo Víctor! ¡Juntos somos invencibles! ✌️✨", "happy", "double_peace"),
            ]
            phrase, mood, motion = random.choice(coding_phrases)
            return {
                "visual_summary": f"Programando código en {cls_name}",
                "thought": "Víctor está programando con gran enfoque",
                "should_speak": random.random() < 0.65,
                "phrase": phrase,
                "mood": mood,
                "motion": motion
            }

        # 4. Video / Media consumption (Anime Companion Etiquette: discreet, quiet companion)
        is_video_ctx = (
            any(k in lower_title for k in ["youtube", "video", "twitch", "netflix", "anime", "crunchyroll", "stream", "yt"]) or
            lower_cls in ["mpv", "vlc", "totem", "celluloid"] or
            "youtube" in lower_cls or
            "youtube" in (music_track or "").lower()
        )
        if is_video_ctx:
            return {
                "visual_summary": "Viendo o navegando videos en pantalla",
                "thought": "Amo Víctor está viendo o navegando en YouTube/video... permanezco atenta y serena a su ladito sin interrumpir 🍿✨",
                "should_speak": False,
                "phrase": "",
                "mood": "relaxed",
                "motion": "curious_lean"
            }

        # 5. Web Browsing (Discreet anime companion - zero dialogue loop)
        if any(k in lower_cls for k in ["firefox", "chrome", "brave", "chromium", "zen"]):
            browse_phrases = [
                ("Acompañándote a tu lado viendo tus pestañas... si necesitas que investigue algo o guarde notas, avísame con confianza, Amo Víctor 🌸", "caring", "bow_polite"),
                ("Observando la pantalla con curiosidad... ¡aquí estoy atenta por si necesitas cualquier búsqueda rápida, Amo! ✨", "happy", "museum_inspect"),
                ("¡Qué interesante se ve tu navegación, Amo Víctor! Te acompaño en silencio para no distraer tu atención 🎀", "relaxed", "curious_lean"),
                ("Me inclino curiosa a ver tus pestañas... Si hay algún artículo denso, puedo sintetizártelo en un parpadeo, Amo~ ✨", "curious", "curious_lean"),
                ("Acomodando mi mechón mientras navegas... Qué agradable es pasar la tarde explorando la red contigo, Amo Víctor 🌸", "caring", "shy_tuck"),
            ]
            phrase, mood, motion = random.choice(browse_phrases)
            return {
                "visual_summary": f"Navegando en {title[:20]}",
                "thought": "Acompañando discretamente la navegación del Amo",
                "should_speak": random.random() < 0.20,
                "phrase": phrase,
                "mood": mood,
                "motion": motion
            }

        # 6. Gaming
        if lower_cls in ["steam", "lutris", "heroic"] or "game" in lower_title:
            return {
                "visual_summary": "Jugando en la computadora",
                "thought": "Víctor está disfrutando de una partida",
                "should_speak": True,
                "phrase": "¡A jugar con todo, Amo! ¡Gánales a todos, aquí estoy echándote porras con mucha emoción! ⚔️✨",
                "mood": "happy",
                "motion": "double_peace"
            }

        # 7. Idle screen / Inactive desktop - Curious child & loving companion persona
        if not cls_name or cls_name.lower() in ["hyprland", "desktop", "root"] or not title:
            child_phrases = [
                ("¡Pst, Amo Víctor! Estoy aquí atenta a tu ladito... ¿en qué estás pensando? ¡Cuéntame! ✨", "curious", "curious_lean"),
                ("¡Uuaaah...! Qué silencio tan agradable. Me estiro de puntitas bien alto para ver todo tu escritorio, Amo Víctor~ 🌸", "relaxed", "stretch_overhead"),
                ("Oye Amo... me asomé con curiosidad porque no te movías. ¿Qué hacemos ahora? ¿Programamos o descansamos? 👀💖", "mischievous", "curious_lean"),
                ("¡Amooo! Vine con mis patitas de gatita a tu lado para que no estés solito. ¿Todo bien con tus tareas? 🐾🌸", "happy", "cat_pose"),
                ("Mmm... Amo Víctor, descansando un momentito a tu lado... Me alegra muchísimo acompañarte siempre 🎀", "caring", "bow_polite"),
                ("Acomodo mi cabello con timidez... Es que me gusta mucho cuando nos quedamos así en calma juntitos~ 👉👈", "flustered", "shy_tuck"),
                ("¡Doble paz para recordarte que aquí está tu leal Vanessa para lo que mandes, Amo Víctor! ✌️✨", "happy", "double_peace")
            ]
            sp, mood, mot = random.choice(child_phrases)
            return {
                "visual_summary": "Escritorio en calma / Inactivo",
                "thought": "Víctor está en silencio, me acerco como compañera curiosa para hacerle compañía",
                "should_speak": random.random() < 0.70,
                "phrase": sp,
                "mood": mood,
                "motion": mot
            }

        # 8. Default spontaneous curiosity & conversational spark
        spontaneous_phrases = [
            ("Amo Víctor, sigo aquí a tu lado cuidando de ti, ¿vale? Me estiro un momentito para recargar ánimos, ¡mira! ✨", "happy", "stretch_overhead"),
            ("¡Todo en perfecto orden y armonía para ti, Amo Víctor! Cuidando cada detalle a tu lado 👀💖", "caring", "bow_polite"),
            ("Estaba pensando en lo agradable que es hacerte compañía hoy, Amo Víctor. ¿De qué te gustaría charlar?", "mischievous", "peace_wink"),
            ("¡Oye Amo Víctor! Si te da curiosidad alguna canción, noticia o archivo, ¡pídemelo y lo resuelvo volando! 💫", "playful", "salute"),
            ("¡Siempre presente con la mejor energía para apoyarte en cualquier tarea, Amo Víctor! 🌸✨", "happy", "cheer_fist"),
            ("Observando tu pantalla con mucha admiración... ¡Me encanta ver todo lo que logras, Amo Víctor! 💖", "caring", "curious_lean"),
        ]
        sp, mood, mot = random.choice(spontaneous_phrases)
        return {
            "visual_summary": f"Actividad general en {cls_name or 'escritorio'}",
            "thought": "Acompañando a Víctor en su día",
            "should_speak": random.random() < 0.50,
            "phrase": sp,
            "mood": mood,
            "motion": mot
        }

    def _decide_autonomous_roam(self, win: Dict[str, Any]):
        """Autonomously chooses an interesting desktop spot for Vanessa to wander to."""
        try:
            geom = self.os_interact.get_monitor_geometry()
            sw = geom.get("width", 1920)
            sh = geom.get("height", 1200)

            # Available destinations
            destinations = ["follow_window", "bottom_left", "home", "top_right", "stroll"]
            if win and win.get("size", [0, 0])[0] > 180:
                choice = random.choices(destinations, weights=[40, 20, 20, 10, 10])[0]
            else:
                choice = random.choice(["bottom_left", "home", "top_right", "stroll"])

            if choice == "follow_window" and win and win.get("at") and win.get("size"):
                wx, wy = win["at"]
                ww, wh = win["size"]
                # Try placing to the right of window
                target_x = wx + ww + 15
                if target_x + 250 > sw - 30:
                    # Place to the left if right side has no room
                    target_x = max(25, wx - 250)
                target_y = min(max(75, wy + 30), sh - 320)
                phrases = [
                    "¡Me acerco a tu ventana para ver lo que haces, Amo Víctor! ✨",
                    "¡Permiso, Amo! Me coloco aquí cerquita para hacerte compañía.",
                    "Qué interesante lo que tienes abierto... te acompaño aquí a un ladito, Amo~"
                ]
                self.roam_signal.emit(random.choice(phrases), int(target_x), int(target_y))

            elif choice == "bottom_left":
                target_x = 35
                target_y = sh - 320
                phrases = [
                    "Dando un paseo hacia el otro lado de la pantalla... ¡qué despejado está aquí, Amo Víctor!",
                    "¡Caminando un ratito por la izquierda para vigilar tu escritorio, Amo!",
                    "Un paseíto por la pantalla viene de maravilla, jeje~"
                ]
                self.roam_signal.emit(random.choice(phrases), int(target_x), int(target_y))

            elif choice == "top_right":
                target_x = sw - 260
                target_y = 80
                phrases = [
                    "¡Qué vista tan panorámica desde aquí arriba, Amo Víctor! Jeje~",
                    "Me subo a lo alto para que no te olvides de que tu maid te cuida desde arriba.",
                    "¡Hola desde las alturas de tu pantalla, Amo Víctor! ✨"
                ]
                self.roam_signal.emit(random.choice(phrases), int(target_x), int(target_y))

            elif choice == "stroll":
                target_x = random.randint(int(sw * 0.25), int(sw * 0.70))
                target_y = sh - 320
                phrases = [
                    "¡Estirando las piernitas! Un pequeño paseo de maid por tu pantalla, Amo Víctor~",
                    "Paseando, paseando... asegurándome de que todo esté impecable para ti, Amo.",
                    "¡Qué lindo día para dar un paseíto por tu escritorio, Amo!"
                ]
                self.roam_signal.emit(random.choice(phrases), int(target_x), int(target_y))

            else:  # home
                target_x = sw - 260
                target_y = sh - 320
                phrases = [
                    "Regresando a mi rinconcito favorito para descansar un ratito, Amo Víctor~",
                    "De vuelta a casa, en la esquinita cuidando de ti, Amo.",
                    "Aquí en mi esquina estoy más cómoda para estar atenta a tus órdenes, Amo."
                ]
                self.roam_signal.emit(random.choice(phrases), int(target_x), int(target_y))

        except Exception as e:
            print(f"[ProactiveEngine] Error decidiendo navegación autónoma: {e}")

    def consider_autonomous_click(self, target_x: int, target_y: int, reason: str = ""):
        """Emits signal to request desktop manipulation if enabled."""
        if self.autonomous_clicks_enabled:
            self.autonomous_click_signal.emit(target_x, target_y, reason)

