"""
Autonomous Desktop Life Engine for Vanessa.
Manages spontaneous proactive thoughts, screen awareness, micro-expressions,
dynamic standby cycles, museum explorer wandering, and Animator-vs-Animation desktop playfulness.
"""
import random
import threading
import asyncio
from PyQt6.QtCore import QObject, QTimer, QRect
from PyQt6.QtWidgets import QApplication
from core.ai_intelligence_hub import AIIntelligenceHub


class DesktopLifeEngine(QObject):
    def __init__(self, overlay, check_interval_ms: int = 24000):
        super().__init__(overlay)
        self.overlay = overlay
        self.autonomous_life_enabled = True
        self.standby_cycles_count = 0
        self.ai_hub = AIIntelligenceHub(overlay)

        self.life_timer = QTimer(self)
        self.life_timer.timeout.connect(self.check_desktop_life)
        self.life_timer.start(check_interval_ms)

    def check_desktop_life(self):
        ov = self.overlay
        if not self.autonomous_life_enabled or ov.current_alpha < 0.5:
            return
        if ov.tts.is_speaking or ov.anim_state == "talking":
            return

        self.standby_cycles_count += 1

        # Periodically cycle standby postures, stretching, crouching or playful personality gestures when peacefully idle
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            if ov.anim_state == "idle" and not ov.tts.is_speaking and not getattr(ov, "is_roaming", False):
                roll = random.random()

                # If idle for 2 or more cycles, Vanessa gets bored and starts wandering like in a museum / Animator vs Animation
                if self.standby_cycles_count >= 2 and roll < 0.45:
                    self._trigger_museum_explorer_roam()
                    self.standby_cycles_count = 0
                    return

                is_media_active = getattr(getattr(ov, "multimedia", None), "is_video_mode", False) or getattr(getattr(ov, "multimedia", None), "current_media_playing", False)
                if roll < 0.18:
                    # Spontaneous gentle stretch
                    ov.vrm_widget.play_gesture("stretch_overhead")
                    if not is_media_active and random.random() < 0.20:
                        phrases = [
                            "¡Uuaaah...! Qué bien sienta estirarse de puntitas un momento ✨",
                            "Estirando los bracitos y la espalda... ¡Amo Víctor, estírate un ratito conmigo! 🌸",
                            "¡Mmhh...! Un buen estiramiento para recargar energías y cuidar de ti 💖"
                        ]
                        ov.show_balloon(random.choice(phrases), duration_ms=4500)
                elif roll < 0.32:
                    # Spontaneous inspection
                    ov.vrm_widget.start_motion("look_around")
                    if not is_media_active and random.random() < 0.20:
                        phrases = [
                            "Mirando con curiosidad su escritorio... ¡todo limpio y ordenado, Amo Víctor! 👀✨",
                            "Observando los alrededores... ¡aquí vigilo atentamente su reino digital! 💖",
                            "¡Inspección minuciosa de maid! No hay ni un solo detalle fuera de lugar 🎀"
                        ]
                        ov.show_balloon(random.choice(phrases), duration_ms=4500)
                elif roll < 0.60:
                    ov.vrm_widget.play_playful_motion()
                else:
                    ov.vrm_widget.play_standby_pose()

        if hasattr(ov, "proactive_engine"):
            ov.proactive_engine.trigger_proactive_cycle()

    def _trigger_museum_explorer_roam(self):
        """Vanessa gets bored standing still, explores the desktop like an art gallery, and reacts dynamically."""
        ov = self.overlay
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1080)
        sw = geom.width()
        sh = geom.height()

        active_win = self.ai_hub.get_current_active_window()
        cur_pos = ov.get_current_screen_pos() if hasattr(ov, "get_current_screen_pos") else ov.pos()

        # Decide destination based on screen content (dynamic video vs static work)
        is_dynamic = False
        target_x = random.randint(120, sw - ov.width() - 80)
        target_y = sh - ov.height() - 35  # Stay grounded on desktop floor

        if active_win:
            title = active_win.get("title", "").lower()
            app_cls = active_win.get("class", "").lower()
            win_at = active_win.get("at", [0, 0])
            win_size = active_win.get("size", [800, 600])

            # Dynamic Multimedia (YouTube, Twitch, Video)
            if any(k in title or k in app_cls for k in ["youtube", "video", "mpv", "twitch", "media", "netflix"]):
                is_dynamic = True
                # Walk towards the edge of the video window to watch together
                win_right = win_at[0] + win_size[0]
                target_x = max(30, min(sw - ov.width() - 35, win_right - 40))

        # Check that we actually move a noticeable distance
        if abs(target_x - cur_pos.x()) < 120:
            target_x = 180 if cur_pos.x() > sw // 2 else sw - ov.width() - 60

        def _on_museum_arrived():
            motion_name, comment = self.ai_hub.execute_playful_window_interaction()
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.start_motion(motion_name)
            if comment:
                ov.show_balloon(comment, duration_ms=5000)

        # Roam stroll
        ov.smooth_roam_to(
            target_x, target_y,
            mode="stroll",
            comment="Paseando curiosa por el escritorio... 🐾✨",
            on_arrived=_on_museum_arrived
        )

    def on_proactive_reaction(self, phrase: str, mood: str, motion: str, should_speak: bool):
        ov = self.overlay
        ov.wake_up()
        ov.set_temporary_state(mood, duration_ms=4500)
        ov.show_balloon(phrase, duration_ms=5000)
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_emotion(mood)
            motion_map = {
                "happy": "heart_hands",
                "playful": "peace_wink",
                "caring": "offer_palm",
                "surprised": "curious_lean",
                "thinking": "think_chin",
                "relaxed": "sigh_relief",
                "stretch": "stretch_overhead",
                "stretch_up": "stretch_overhead",
                "crouch": "curious_lean",
                "crouch_down": "curious_lean"
            }
            target_motion = motion if (motion and motion != "TapBody") else motion_map.get(mood, "talking" if should_speak else "curious_lean")
            if target_motion in ("maid_sit", "sit", "sitting", "sit_kneel", "sit_casual", "crouch", "squat", "japanese_squat", "thinking_squat", "seiza_maid", "side_sit", "side_sit_stay", "bajada", "agacharse"):
                target_motion = "curious_lean"
            procedural_gestures = {
                "curious_lean", "shy_tuck", "smug_cross", "cat_pose",
                "double_peace", "peace_wink", "bow_polite", "museum_inspect",
                "think_chin", "heart_hands",
                "stretch_overhead", "rub_eye_sleepy", "salute", "nod", "head_tilt",
                "tsundere_stand", "cheeks_kawaii", "cover_mouth_giggle",
                "cheer_fist", "victory_jump", "clap_small", "hair_twirl", "shrug", "offer_palm"
            }
            if target_motion in procedural_gestures:
                ov.vrm_widget.play_gesture(target_motion)
            else:
                ov.vrm_widget.start_motion(target_motion)
        if should_speak:
            threading.Thread(
                target=lambda: asyncio.run(ov.tts.speak(phrase, mood=mood)),
                daemon=True
            ).start()

    def on_voice_only_reaction(self, phrase: str, mood: str):
        """Vanessa speaks ambiently WITHOUT showing a dialogue balloon for natural conversation."""
        ov = self.overlay
        ov.wake_up()
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_emotion(mood)
        threading.Thread(
            target=lambda: asyncio.run(ov.tts.speak_without_balloon(phrase, mood=mood)),
            daemon=True
        ).start()

    def on_spontaneous_emotion(self, expression_name: str, weight: float):
        """Sets spontaneous micro-expressions on the 3D VRM model."""
        ov = self.overlay
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_expression(expression_name, weight)

    def on_proactive_thought(self, thought: str, mood: str):
        ov = self.overlay
        if not ov.balloon_text:
            ov.set_temporary_state(mood, duration_ms=3500)
            ov.show_balloon(f"💭 {thought}", duration_ms=3800)

    def toggle_autonomous_life(self):
        ov = self.overlay
        self.autonomous_life_enabled = not self.autonomous_life_enabled
        state_str = "activadas" if self.autonomous_life_enabled else "pausadas"
        ov.show_balloon(f"🌟 Reacciones en pantalla {state_str}", duration_ms=3000)
