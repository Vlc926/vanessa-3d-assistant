import time
import random
import threading
import asyncio
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, QTimer, QRect
from PyQt6.QtWidgets import QApplication
from core.ai_intelligence_hub import AIIntelligenceHub

class DesktopLifeEngine(QObject):
    def __init__(self, overlay, check_interval_ms: int = 16000):
        super().__init__(overlay if isinstance(overlay, QObject) else None)
        self.overlay = overlay
        self.autonomous_life_enabled = True
        self.standby_cycles_count = 0
        self.ai_hub = AIIntelligenceHub(overlay)
        self.last_user_activity_time = time.time()
        self.last_window_react_time = 0.0
        self.last_pose_name = ""
        self.last_window_addr = ""
        self.is_throttled = False
        self.pose_history: List[str] = []

        self.life_timer = QTimer(self)
        self.life_timer.timeout.connect(self.check_desktop_life)
        self.life_timer.start(check_interval_ms)

        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self.check_inactivity_watchdog)
        self.watchdog_timer.start(5000)

        QTimer.singleShot(1500, self._bind_controllers)

    def _bind_controllers(self):
        ov = self.overlay
        if hasattr(ov, "hypr_controller") and ov.hypr_controller:
            try:
                ov.hypr_controller.active_window_changed.connect(self.on_active_window_changed)
            except Exception:
                pass

    def notify_user_activity(self):
        self.last_user_activity_time = time.time()
        if self.is_throttled:
            self.is_throttled = False
            ov = self.overlay
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.set_throttling(False, 30.0)
                ov.vrm_widget.notify_activity("action")

    def check_inactivity_watchdog(self):
        ov = self.overlay
        if not self.autonomous_life_enabled or ov.current_alpha < 0.5:
            return
        if ov.tts.is_speaking or ov.anim_state == "talking" or getattr(ov, "is_roaming", False):
            self.notify_user_activity()
            return

        now = time.time()
        idle_duration = now - self.last_user_activity_time

        if idle_duration > 60.0 and not self.is_throttled:
            self.is_throttled = True
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.set_throttling(True, 15.0)
                gentle_idle_poses = ["relax", "bow_polite", "standby", "idle_maid"]
                self.play_intercalated_pose(gentle_idle_poses)

    def on_active_window_changed(self, win: Dict[str, Any]):
        self.notify_user_activity()
        ov = self.overlay
        if not self.autonomous_life_enabled or ov.current_alpha < 0.5:
            return
        if ov.tts.is_speaking or ov.anim_state == "talking" or getattr(ov, "is_roaming", False):
            return

        now = time.time()
        addr = win.get("address", "")
        if addr == self.last_window_addr and (now - self.last_window_react_time) < 20.0:
            return
        self.last_window_addr = addr
        self.last_window_react_time = now

        win_cls = (win.get("class") or "").lower()
        win_title = (win.get("title") or "").lower()

        if any(k in win_cls for k in ["code", "nvim", "vim", "kitty", "alacritty", "wezterm", "terminal"]):
            code_poses = ["think_chin", "thinking", "inspect", "ritsu_calc", "cheer_fist", "curious_lean", "pout"]
            self.play_intercalated_pose(code_poses)
        elif any(k in win_cls or k in win_title for k in ["youtube", "spotify", "mpv", "vlc"]):
            media_poses = ["relax", "dance_reze", "happy_gesture", "clapping", "heart_hands", "peace_wink"]
            self.play_intercalated_pose(media_poses)
        elif any(k in win_cls for k in ["firefox", "chrome", "chromium", "brave", "zen", "edge"]):
            browse_poses = ["inspect_window_read", "look_around", "curious_lean", "museum_inspect", "fairy_scan"]
            self.play_intercalated_pose(browse_poses)

    def play_intercalated_pose(self, candidate_pool: List[str]):
        ov = self.overlay
        if not getattr(ov, "using_vrm", False) or not hasattr(ov, "vrm_widget"):
            return
        if not candidate_pool:
            return

        available = [p for p in candidate_pool if p != self.last_pose_name and p not in self.pose_history[-2:]]
        chosen = random.choice(available if available else candidate_pool)

        self.last_pose_name = chosen
        self.pose_history.append(chosen)
        if len(self.pose_history) > 10:
            self.pose_history.pop(0)

        ov.vrm_widget.notify_activity("action")
        if hasattr(ov.vrm_widget, "play_gesture"):
            ov.vrm_widget.play_gesture(chosen)
        elif hasattr(ov.vrm_widget, "start_motion"):
            ov.vrm_widget.start_motion(chosen)

    def check_desktop_life(self):
        ov = self.overlay
        if not self.autonomous_life_enabled or ov.current_alpha < 0.5:
            return
        if ov.tts.is_speaking or ov.anim_state == "talking":
            return

        self.standby_cycles_count += 1

        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            if ov.anim_state == "idle" and not ov.tts.is_speaking and not getattr(ov, "is_roaming", False):
                roll = random.random()

                if self.standby_cycles_count >= 2 and roll < 0.55:
                    self.standby_cycles_count = 0
                    if hasattr(ov, "screen_interact") and random.random() < 0.70:
                        active_win = ov.screen_interact.get_active_hyprland_window()
                        if active_win and not getattr(ov.screen_interact, "is_currently_perched", False):
                            sub_roll = random.random()
                            if sub_roll < 0.50:
                                ov.screen_interact.perch_on_window_border(active_win, style="sit")
                            elif sub_roll < 0.75:
                                ov.screen_interact.perch_on_window_border(active_win, style="crouch")
                            else:
                                ov.screen_interact.slide_on_window_scrollbar(active_win)
                            return
                    self._trigger_museum_explorer_roam()
                    return

                is_media_active = getattr(getattr(ov, "multimedia", None), "is_video_mode", False) or getattr(getattr(ov, "multimedia", None), "current_media_playing", False)
                active_win = ov.screen_interact.get_active_hyprland_window() if hasattr(ov, "screen_interact") else None
                win_cls = (active_win.get("class") or "").lower() if active_win else ""

                if "code" in win_cls or "nvim" in win_cls or "terminal" in win_cls or "kitty" in win_cls:
                    con_poses = ["thinking", "inspect", "ritsu_calc", "cheer_fist", "curious_lean", "pout"]
                    self.play_intercalated_pose(con_poses)
                elif is_media_active or "youtube" in win_cls or "spotify" in win_cls:
                    media_poses = ["relax", "dance_reze", "happy_gesture", "clapping", "heart_hands"]
                    self.play_intercalated_pose(media_poses)
                elif roll < 0.22:
                    self.play_intercalated_pose(["heart_hands", "cheeks_kawaii", "cover_mouth_giggle"])
                    if not is_media_active and random.random() < 0.20:
                        phrases = [
                            "¡Cuidando atentamente de ti en cada momento, Amo Víctor! ✨",
                            "A su ladito acompañándole mientras trabaja... ¡eres el mejor! 🌸",
                            "¡Todo mi cariño y lealtad siempre para usted, mi Amo! 💖"
                        ]
                        ov.show_balloon(random.choice(phrases), duration_ms=4500)
                elif roll < 0.40:
                    cur_poses = ["look_around", "curious_lean", "museum_inspect", "fairy_scan"]
                    self.play_intercalated_pose(cur_poses)
                    if not is_media_active and random.random() < 0.20:
                        phrases = [
                            "Mirando con curiosidad su escritorio... ¡todo limpio y ordenado, Amo Víctor! 👀✨",
                            "Observando los alrededores... ¡aquí vigilo atentamente su reino digital! 💖",
                            "¡Inspección minuciosa de maid! No hay ni un solo detalle fuera de lugar 🎀"
                        ]
                        ov.show_balloon(random.choice(phrases), duration_ms=4500)
                elif roll < 0.68:
                    ov.vrm_widget.play_playful_motion()
                else:
                    ov.vrm_widget.play_standby_pose()

        if hasattr(ov, "proactive_engine"):
            ov.proactive_engine.trigger_proactive_cycle()

    def _trigger_museum_explorer_roam(self):
        ov = self.overlay
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1080)
        sw = geom.width()
        sh = geom.height()

        active_win = self.ai_hub.get_current_active_window()
        cur_pos = ov.get_current_screen_pos() if hasattr(ov, "get_current_screen_pos") else ov.pos()

        target_x = random.randint(120, sw - ov.width() - 80)
        target_y = sh - ov.height() - 35

        if active_win:
            title = active_win.get("title", "").lower()
            app_cls = active_win.get("class", "").lower()
            win_at = active_win.get("at", [0, 0])
            win_size = active_win.get("size", [800, 600])

            if any(k in title or k in app_cls for k in ["youtube", "video", "mpv", "twitch", "media", "netflix"]):
                win_right = win_at[0] + win_size[0]
                target_x = max(30, min(sw - ov.width() - 35, win_right - 40))

        if abs(target_x - cur_pos.x()) < 120:
            target_x = 180 if cur_pos.x() > sw // 2 else sw - ov.width() - 60

        def _on_museum_arrived():
            motion_name, comment = self.ai_hub.execute_playful_window_interaction()
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.start_motion(motion_name)
            if comment:
                ov.show_balloon(comment, duration_ms=5000)

        ov.smooth_roam_to(
            target_x, target_y,
            mode="stroll",
            comment="Paseando curiosa por el escritorio... 🐾✨",
            on_arrived=_on_museum_arrived
        )

    def on_proactive_reaction(self, phrase: str, mood: str, motion: str, should_speak: bool):
        self.notify_user_activity()
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
                "relaxed": "relax",
                "stretch": "heart_hands",
                "stretch_up": "peace_wink",
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
                "cheer_fist", "victory_jump", "clap_small", "hair_twirl", "shrug", "offer_palm",
                "perch_window_sit", "perch_window_dangle", "perch_edge_crouch", "inspect_window_read", "slide_scrollbar"
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
        self.notify_user_activity()
        ov = self.overlay
        ov.wake_up()
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_emotion(mood)
        threading.Thread(
            target=lambda: asyncio.run(ov.tts.speak_without_balloon(phrase, mood=mood)),
            daemon=True
        ).start()

    def on_spontaneous_emotion(self, expression_name: str, weight: float):
        self.notify_user_activity()
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
