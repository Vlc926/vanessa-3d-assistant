import math
import time
import random
import subprocess
import json
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, QTimer, QRect
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from src.perception.actuator import Actuator
from src.visual.two_bone_ik import TwoBoneIKSolver

class ScreenInteractor(QObject):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.autonomous_clicks_enabled = False
        self.is_currently_perched = False
        self.current_perched_window = None
        self.close_panic_active = False
        self.actuator = Actuator(execute_real=True)
        self.hand_ik_solver = TwoBoneIKSolver(l1=0.28, l2=0.26)

        self.mouse_tracking_enabled = self.overlay.brain.personality.get("mouse_tracking", True)
        self.mouse_track_timer = QTimer(self)
        self.mouse_track_timer.timeout.connect(self.track_cursor_for_vrm)
        if self.mouse_tracking_enabled:
            self.mouse_track_timer.start(90)

    def _check_perched_window_state(self, cx: Optional[float], cy: Optional[float]):
        if not self.is_currently_perched or not self.current_perched_window:
            return
        ov = self.overlay
        target_addr = str(self.current_perched_window.get("address", "")).lower()
        wins = self.get_hyprland_windows()
        matched = None
        for w in wins:
            if str(w.get("address", "")).lower() == target_addr:
                matched = w
                break
        if not matched:
            self.is_currently_perched = False
            self.current_perched_window = None
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.set_reading_mode(False)
                ov.vrm_widget.set_perched(False)
                ov.vrm_widget.trigger_window_close_panic(False)
            if hasattr(ov, "physics_engine") and ov.physics_engine:
                ov.physics_engine.release_drag(float(ov.x()), float(ov.y()))
            return

        self.current_perched_window = matched
        if cx is not None and cy is not None:
            wx = float(matched.get("x", 0))
            wy = float(matched.get("y", 0))
            ww = float(matched.get("w", 0))
            close_btn_x = wx + ww - 24.0
            close_btn_y = wy + 18.0
            dist_to_close = math.hypot(cx - close_btn_x, cy - close_btn_y)
            if dist_to_close < 70.0:
                if not self.close_panic_active:
                    self.close_panic_active = True
                    if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "trigger_window_close_panic"):
                        ov.vrm_widget.trigger_window_close_panic(True)
                    ov.show_balloon("¡Nooo Amo Víctor, no cierre esta ventana que me caigo! 😱💦", duration_ms=3000)
            elif self.close_panic_active:
                self.close_panic_active = False
                if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "trigger_window_close_panic"):
                    ov.vrm_widget.trigger_window_close_panic(False)

    def track_cursor_for_vrm(self):
        ov = self.overlay
        if not getattr(ov, "using_vrm", False) or not hasattr(ov, "vrm_widget") or not self.mouse_tracking_enabled:
            return
        try:
            cx, cy = None, None
            if hasattr(ov, "perception_daemon") and ov.perception_daemon:
                c = getattr(ov.perception_daemon, "cached_cursor", {})
                if c and "x" in c and "y" in c:
                    cx, cy = float(c["x"]), float(c["y"])
            if cx is None or cy is None:
                out = subprocess.check_output(["hyprctl", "cursorpos"], stderr=subprocess.DEVNULL, text=True)
                parts = [p.strip() for p in out.strip().split(",")]
                if len(parts) == 2:
                    cx, cy = float(parts[0]), float(parts[1])
            if self.is_currently_perched:
                self._check_perched_window_state(cx, cy)
                return
            if cx is not None and cy is not None:
                vx = ov.x() + (ov.width() / 2.0)
                vy = ov.y() + (ov.height() / 2.0)
                screens = QApplication.screens()
                geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
                sw = geom.width()
                sh = geom.height()
                norm_x = (cx - vx) / (sw / 2.0)
                norm_y = -(cy - vy) / (sh / 2.0)
                norm_x = max(-1.0, min(1.0, norm_x))
                norm_y = max(-1.0, min(1.0, norm_y))
                ov.vrm_widget.look_at(norm_x, norm_y)
        except Exception:
            pass

    def get_hyprland_windows(self) -> List[Dict[str, Any]]:
        windows = []
        try:
            if hasattr(self.overlay, "perception_daemon") and self.overlay.perception_daemon:
                raw_clients = getattr(self.overlay.perception_daemon.projector, "cached_clients", None)
                if raw_clients:
                    for w in raw_clients:
                        if w.get("mapped", False) and not w.get("hidden", False):
                            at = w.get("at", [0, 0])
                            size = w.get("size", [0, 0])
                            if size[0] > 120 and size[1] > 100:
                                windows.append({
                                    "address": w.get("address", ""),
                                    "x": at[0],
                                    "y": at[1],
                                    "w": size[0],
                                    "h": size[1],
                                    "title": w.get("title", ""),
                                    "class": w.get("class", ""),
                                    "initialClass": w.get("initialClass", ""),
                                    "pid": w.get("pid", 0)
                                })
                    if windows:
                        return windows
            out = subprocess.check_output(["hyprctl", "clients", "-j"], stderr=subprocess.DEVNULL, text=True)
            data = json.loads(out)
            for w in data:
                if w.get("mapped", False) and not w.get("hidden", False):
                    at = w.get("at", [0, 0])
                    size = w.get("size", [0, 0])
                    if size[0] > 120 and size[1] > 100:
                        windows.append({
                            "address": w.get("address", ""),
                            "x": at[0],
                            "y": at[1],
                            "w": size[0],
                            "h": size[1],
                            "title": w.get("title", ""),
                            "class": w.get("class", ""),
                            "initialClass": w.get("initialClass", ""),
                            "pid": w.get("pid", 0)
                        })
        except Exception:
            pass
        return windows

    def get_active_hyprland_window(self) -> Optional[Dict[str, Any]]:
        try:
            if hasattr(self.overlay, "perception_daemon") and self.overlay.perception_daemon:
                active_addr = getattr(self.overlay.perception_daemon, "cached_active_address", "")
                raw_clients = getattr(self.overlay.perception_daemon.projector, "cached_clients", None)
                if active_addr and raw_clients:
                    for w in raw_clients:
                        if w.get("address", "").lower() == active_addr.lower():
                            at = w.get("at", [0, 0])
                            size = w.get("size", [0, 0])
                            return {
                                "address": w.get("address", ""),
                                "x": at[0],
                                "y": at[1],
                                "w": size[0],
                                "h": size[1],
                                "title": w.get("title", ""),
                                "class": w.get("class", ""),
                                "pid": w.get("pid", 0)
                            }
            out = subprocess.check_output(["hyprctl", "activewindow", "-j"], stderr=subprocess.DEVNULL, text=True)
            data = json.loads(out)
            at = data.get("at", [0, 0])
            size = data.get("size", [0, 0])
            if size[0] > 100 and size[1] > 80:
                return {
                    "address": data.get("address", ""),
                    "x": at[0],
                    "y": at[1],
                    "w": size[0],
                    "h": size[1],
                    "title": data.get("title", ""),
                    "class": data.get("class", ""),
                    "pid": data.get("pid", 0)
                }
        except Exception:
            pass
        return None

    def perch_on_window_border(self, window_info: Optional[Dict[str, Any]] = None, style: str = "sit"):
        ov = self.overlay
        ov.wake_up()

        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        target = window_info or self.get_active_hyprland_window()
        if not target:
            all_wins = self.get_hyprland_windows()
            if all_wins:
                target = all_wins[0]

        if not target:
            self.curious_inspect_screen()
            return

        wx, wy, ww, wh = target["x"], target["y"], target["w"], target["h"]
        title = target.get("title") or target.get("class") or "tu ventana"

        tx = wx + (ww // 2) - (ov.width() // 2)
        tx = max(25, min(sw - ov.width() - 30, tx))

        overlap_offset = int(ov.height() * 0.22)
        ty = wy - ov.height() + overlap_offset
        ty = max(20, min(sh - ov.height() - 35, ty))

        self.current_perched_window = target

        def _on_perch_arrived():
            self.is_currently_perched = True
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.set_perched(True, style)
                ov.vrm_widget.set_expression("relaxed", 0.9)
                ov.vrm_widget.look_at(0.0, -0.45)
                ov.vrm_widget.set_reading_mode(True)

            read_greetings = [
                f"Me he posado aquí para acompañarle mientras trabaja en '{title[:22]}', Amo Víctor ✨",
                f"Observando con curiosidad su contenido de '{title[:24]}', Amo Víctor 👀💖",
                f"¡Aquí estoy sentadita junto a usted, Amo! Leyendo con mucha atención ✨",
                f"¡Qué vista tan privilegiada de su pantalla, Amo Víctor! Aquí me quedo descansando con usted 🌸",
            ]
            msg = random.choice(read_greetings)
            ov.show_balloon(msg, duration_ms=5000)

            self.read_and_learn_context(target)

            QTimer.singleShot(14000, self.unperch_and_roam_home)

        ov.smooth_roam_to(
            tx, ty,
            mode="curious",
            comment="¡Voy a posarme con mucho cuidado en su ventana para acompañarlo! 🌸✨",
            on_arrived=_on_perch_arrived
        )

    def unperch_and_roam_home(self):
        ov = self.overlay
        if not self.is_currently_perched:
            return
        self.is_currently_perched = False
        self.current_perched_window = None

        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_reading_mode(False)
            ov.vrm_widget.set_perched(False)
            ov.vrm_widget.look_at(0.0, 0.0)

        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        home_x = geom.width() - ov.width() - 40
        home_y = geom.height() - ov.height() - 55

        ov.smooth_roam_to(
            home_x, home_y,
            mode="relaxed",
            comment="Regresando con delicadeza a mi posición principal, Amo Víctor ✨",
            on_arrived=ov.reset_to_idle
        )

    def slide_on_window_scrollbar(self, window_info: Optional[Dict[str, Any]] = None):
        ov = self.overlay
        ov.wake_up()

        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        target = window_info or self.get_active_hyprland_window()
        if not target:
            return

        wx, wy, ww, wh = target["x"], target["y"], target["w"], target["h"]
        title = target.get("title") or target.get("class") or "la ventana"

        tx = min(sw - ov.width() - 25, wx + ww - int(ov.width() * 0.45))
        ty = max(70, min(sh - ov.height() - 40, wy + int(wh * 0.28)))

        def _on_slide_arrived():
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.start_motion("slide_scrollbar")
                ov.vrm_widget.set_expression("happy", 0.95)

            msg = f"¡Deslizándome por la barra de desplazamiento de '{title[:20]}'! ¡Qué divertido, Amo Víctor! 🎢✨"
            ov.show_balloon(msg, duration_ms=4500)
            if hasattr(ov, "tts"):
                ov.tts.speak_async(msg, mood="happy")

            QTimer.singleShot(5000, self.unperch_and_roam_home)

        ov.smooth_roam_to(
            tx, ty,
            mode="playful",
            comment="¡Voy a deslizarme por la barra lateral de la ventana! 💫",
            on_arrived=_on_slide_arrived
        )

    def read_and_learn_context(self, window_info: Dict[str, Any]):
        ov = self.overlay
        title = window_info.get("title", "")
        wclass = window_info.get("class", "")
        if not title and not wclass:
            return

        def _async_learn():
            prompt = (
                f"El Amo Víctor está utilizando la aplicación '{wclass}' con el título/documento: '{title}'. "
                "Como Vanessa, con tus 8 virtudes unificadas (Amadeus, Isla, Vivy, Schwi, Hada, Alice, Strea, Ritsu), "
                "genera una breve reflexión de una sola frase aprendiendo qué hace el Amo o qué conocimientos guarda esto."
            )
            thought = ""
            try:
                thought = ov.brain.think_fast(prompt)
            except Exception:
                thought = f"He aprendido que el Amo Víctor está trabajando con dedicación en {wclass}. ¡Qué admirable!"

            if hasattr(ov, "memory") and thought:
                try:
                    ov.memory.add_proactive_observation(
                        window_class=wclass,
                        window_title=title,
                        visual_summary=f"Lectura autonoma de pantalla: {title[:40]}",
                        vanessa_thought=thought,
                        mood="curious",
                        initiated_dialogue=False
                    )
                except Exception:
                    pass
            if hasattr(ov, "learning_vault") and thought:
                try:
                    ov.learning_vault.add_learning_topic(f"{wclass}: {title[:36]}", category=wclass, notes=thought)
                except Exception:
                    pass

            if thought and getattr(ov, "balloon_text", "") == "":
                ov.show_balloon(f"💡 {thought[:140]}", duration_ms=6000)

        QTimer.singleShot(3500, _async_learn)

    def interactive_press_media(self, action: str = "play_pause", speak: bool = True, media_type: str = "auto"):
        ov = self.overlay
        ov.wake_up()
        a = (action or "play_pause").lower()

        is_video = False
        if media_type == "video" or "video" in a or "youtube" in a:
            is_video = True
        elif media_type == "music" or "music" in a or "cancion" in a or "pista" in a:
            is_video = False
        else:
            is_video = getattr(getattr(ov, "multimedia", None), "is_video_mode", False)

        status = ""
        try:
            status = subprocess.run(["playerctl", "status"], capture_output=True, text=True, timeout=0.6).stdout.strip().lower()
        except Exception:
            pass

        if is_video:
            want_pause = (any(k in a for k in ("pause", "pausar", "deten", "para"))) or (status == "playing" and "play" not in a)
            if want_pause:
                cmd = ["playerctl", "pause"]
                line = random.choice([
                    "Video pausado, Amo Víctor. Aquí lo espero con calma ⏸️🍿",
                    "Pausa en el video. Tómese su tiempo, Amo Víctor 😊",
                    "Video detenido, Amo. Atenta a cuando desee continuar ✨",
                ])
                if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                    ov.vrm_widget.set_expression("relaxed", 0.8)
                    ov.vrm_widget.play_gesture("nod")
            else:
                cmd = ["playerctl", "play"]
                line = random.choice([
                    "Reanudando su video, Amo Víctor ▶️🍿 ¡Que lo disfrute!",
                    "¡Continuamos con el video, Amo! Aquí sigo acompañándolo 👀✨",
                    "Reproduciendo video. Disfrute mucho, Amo Víctor ▶️",
                ])
                if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                    ov.vrm_widget.set_expression("happy", 0.85)
                    ov.vrm_widget.play_gesture("joy")

            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
            except Exception:
                pass

            ov.show_balloon(line, duration_ms=4500)
            if speak and hasattr(ov, "tts"):
                ov.tts.speak_async(line, mood="caring")
            return

        want_pause = (any(k in a for k in ("pause", "pausar", "deten", "para"))) or (status == "playing" and "play" not in a)
        if want_pause:
            cmd = ["playerctl", "pause"]
            gesture = "press_button"
            line = random.choice([
                "Pausando su música con el Walkman, Amo Víctor ⏸️📻",
                "Música en pausa. Aquí guardo su sintonía, Amo 🎵✨",
            ])
        else:
            cmd = ["playerctl", "play"]
            gesture = "press_button"
            line = random.choice([
                "¡Play! Reanudando su música en el Walkman, Amo Víctor ▶️🎶",
                "¡Que siga la buena melodía, Amo! 🎵💖",
            ])

        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            self._apply_ik_hand_reach(int(ov.x() + ov.width() * 0.5), int(ov.y() + ov.height() * 0.4))
            ov.vrm_widget.start_motion(gesture)
            ov.vrm_widget.set_expression("happy", 0.9)

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
        except Exception:
            pass

        ov.show_balloon(line, duration_ms=4500)
        if speak and hasattr(ov, "tts"):
            ov.tts.speak_async(line, mood="happy")

    def quick_tab_action(self, op: str = "new"):
        ov = self.overlay
        ov.wake_up()
        if op == "new":
            ov.os_interact.send_shortcut("ctrl+t")
            msg = "¡Pestaña nueva abierta para ti, Amo Víctor! 🌐✨"
        elif op == "close":
            ov.os_interact.send_shortcut("ctrl+w")
            msg = "Pestaña cerrada con cuidado, Amo. ✂️✨"
        elif op == "next":
            ov.os_interact.send_shortcut("ctrl+Tab")
            msg = "Cambiando a la siguiente pestaña... ⏩"
        else:
            ov.os_interact.send_shortcut("ctrl+shift+Tab")
            msg = "Regresando a la pestaña previa... ⏪"

        ov.show_balloon(msg, duration_ms=3000)

    def interactive_click_button(self, action_type: str):
        ov = self.overlay
        ov.wake_up()
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        target_btn = action_type.lower()
        if "close" in target_btn or "cerrar" in target_btn:
            tx = sw - ov.width() - 40
            ty = 80
            btn_name = "cerrar"
            shortcut = "alt+F4"
        elif "max" in target_btn or "minim" in target_btn:
            tx = sw - ov.width() - 85
            ty = 80
            btn_name = "maximizar"
            shortcut = "super+f"
        else:
            tx = sw // 2 - ov.width() // 2
            ty = sh // 2 - ov.height() // 2
            btn_name = "acción"
            shortcut = "Return"

        def _on_btn_arrived():
            self._apply_ik_hand_reach(tx, ty)
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.start_motion("button_tap")
                ov.vrm_widget.set_expression("happy")

            ov.os_interact.send_shortcut(shortcut)
            msg = f"¡Botón de {btn_name} pulsado para ti, Amo Víctor! ✨"
            ov.show_balloon(msg, duration_ms=3500)
            if hasattr(ov, "tts"):
                ov.tts.speak_async(msg, mood="happy")
            QTimer.singleShot(3500, ov.reset_to_idle)

        ov.smooth_roam_to(
            tx, ty,
            mode="playful",
            comment=f"¡Corriendo a presionar el botón de {btn_name} para ti! 🐾✨",
            on_arrived=_on_btn_arrived
        )

    def curious_inspect_screen(self, target_type: str = "active_window"):
        ov = self.overlay
        ov.wake_up()
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        target_title = "tu trabajo"
        gaze_x = -0.5
        gaze_y = 0.2

        if target_type == "cursor":
            cpos = QCursor.pos()
            tx = max(20, min(sw - ov.width() - 30, cpos.x() + 35))
            ty = max(70, min(sh - ov.height() - 35, cpos.y() - 100))
            target_title = "lo que señala tu cursor"
            gaze_x = -0.6 if cpos.x() < tx else 0.6
            gaze_y = 0.1
            motion_to_play = "look_around"
        else:
            win = self.get_active_hyprland_window()
            if win:
                wx, wy = win["x"], win["y"]
                ww, wh = win["w"], win["h"]
                tx = wx + ww + 15
                if tx + ov.width() > sw - 25:
                    tx = max(25, wx - ov.width() - 15)
                    gaze_x = 0.6
                    motion_to_play = "look_around"
                else:
                    gaze_x = -0.6
                    motion_to_play = "look_around"
                ty = min(max(75, wy + 20), sh - ov.height() - 35)
                target_title = win.get("title") or win.get("class") or "tu pantalla"
            else:
                tx = sw // 2 - ov.width() // 2
                ty = sh - ov.height() - 50
                gaze_x = 0.0
                motion_to_play = "look_around"

        def _on_curious_arrived():
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.look_at(gaze_x, gaze_y)
                ov.vrm_widget.play_gesture(motion_to_play)
                ov.vrm_widget.set_expression("surprised", 0.9)

            remarks = [
                f"Amo Víctor... ¿qué es esto tan interesante que estás viendo en '{target_title[:20]}'? ¡Se ve genial! 👀✨",
                f"¿Qué estamos observando por aquí en '{target_title[:22]}', Amo Víctor? ¡Me da mucha curiosidad! 💖",
                f"¡Ooh! Qué interesante se ve esto en tu pantalla... ¿Qué estás haciendo hoy, Amo Víctor? ✨",
                f"Observando con mucha atención '{target_title[:20]}' para ti, Amo Víctor~ 👀💖",
            ]
            msg = random.choice(remarks)
            ov.show_balloon(msg, duration_ms=5000)
            if hasattr(ov, "tts"):
                ov.tts.speak_async(msg, mood="happy")

            QTimer.singleShot(4200, ov.reset_to_idle)

        ov.smooth_roam_to(
            tx, ty,
            mode="curious",
            comment="¿Mmh? ¿Qué habrá por aquí...? 👀",
            on_arrived=_on_curious_arrived
        )

    def select_and_highlight_text(self, mode: str = "all"):
        ov = self.overlay
        ov.wake_up()
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        win = self.get_active_hyprland_window()
        tx = sw - ov.width() - 40
        ty = sh - ov.height() - 45
        if win:
            wx, wy = win["x"], win["y"]
            ww = win["w"]
            tx = min(max(25, wx + ww + 15), sw - ov.width() - 25)
            if tx + ov.width() > sw - 20:
                tx = max(25, wx - ov.width() - 15)
            ty = min(max(75, wy + 30), sh - ov.height() - 35)

        def _on_select_arrived():
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.look_at(-0.4, 0.1)
                ov.vrm_widget.start_motion("thinking")
                ov.vrm_widget.set_expression("happy")

            if mode == "copy":
                ov.os_interact.send_shortcut("ctrl+a")
                time.sleep(0.06)
                ov.os_interact.send_shortcut("ctrl+c")
                msg = "¡Texto seleccionado y copiado al portapapeles, Amo Víctor! 📋✨"
            elif mode == "line":
                ov.os_interact.send_shortcut("shift+End")
                msg = "¡Línea resaltada para ti, Amo Víctor! 🖍️✨"
            else:
                ov.os_interact.send_shortcut("ctrl+a")
                msg = "¡He seleccionado y resaltado todo el texto para ti, Amo! 📝✨"

            ov.show_balloon(msg, duration_ms=4500)
            if hasattr(ov, "tts"):
                ov.tts.speak_async(msg, mood="happy")

            QTimer.singleShot(3500, ov.reset_to_idle)

        ov.smooth_roam_to(
            tx, ty,
            mode="careful",
            comment="Posicionándome con cuidado para seleccionar el texto... ✍️",
            on_arrived=_on_select_arrived
        )

    def toggle_autonomous_clicks(self):
        ov = self.overlay
        self.autonomous_clicks_enabled = not self.autonomous_clicks_enabled
        if hasattr(ov, "proactive_engine"):
            ov.proactive_engine.autonomous_clicks_enabled = self.autonomous_clicks_enabled
        st = "permitidos" if self.autonomous_clicks_enabled else "desactivados"
        ov.show_balloon(f"🖱️ Clics autónomos {st}", duration_ms=3000)

    def perform_mouse_click(
        self,
        button: str = "left",
        double: bool = False,
        target_x: Optional[int] = None,
        target_y: Optional[int] = None,
        reason: str = ""
    ):
        ov = self.overlay
        ov.wake_up()
        if target_x is not None and target_y is not None:
            self._apply_ik_hand_reach(target_x, target_y)
            if reason:
                ov.show_balloon(f"🖱️ {reason}", duration_ms=3000)
            res = ov.os_interact.click_at(target_x, target_y, button=button, double=double, smooth=True)
        else:
            res = ov.os_interact.click_mouse(button=button, double=double)
        ov.show_balloon(res, duration_ms=3000)

    def _apply_ik_hand_reach(self, target_x: int, target_y: int) -> Dict[str, Any]:
        ov = self.overlay
        shoulder_x = float(ov.x() + ov.width() * 0.5)
        shoulder_y = float(ov.y() + ov.height() * 0.35)
        rel_dx = (float(target_x) - shoulder_x) / 300.0
        rel_dy = (shoulder_y - float(target_y)) / 300.0
        p_root, p_elbow, p_wrist = self.hand_ik_solver.solve(
            [0.0, 0.0, 0.0],
            [rel_dx, rel_dy, 0.15],
            [0.0, -0.2, 0.3]
        )
        crouch = max(0.0, min(0.85, -rel_dy * 0.5)) if rel_dy < -0.15 else 0.0
        tiptoe = max(0.0, min(0.85, rel_dy * 0.5)) if rel_dy > 0.15 else 0.0
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            if hasattr(ov.vrm_widget, "set_vertical_posture_offset"):
                ov.vrm_widget.set_vertical_posture_offset(crouch, tiptoe)
                QTimer.singleShot(1400, lambda: ov.vrm_widget.set_vertical_posture_offset(0.0, 0.0))
            ov.vrm_widget.play_gesture("press_button")
        return {
            "elbow": p_elbow.tolist(),
            "wrist": p_wrist.tolist(),
            "crouch_depth": crouch,
            "tiptoe_height": tiptoe,
        }

    def lie_down_on_window_border(self, window_info: Optional[Dict[str, Any]] = None):
        self.perch_on_window_border(window_info=window_info, style="lie_down")

    def shake_active_window(self, amplitude: int = 12, cycles: int = 3) -> Dict[str, Any]:
        ov = self.overlay
        ov.wake_up()
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.play_gesture("push_window")
            ov.vrm_widget.set_expression("playful", 0.95)
        res = self.actuator.shake_active_window(amplitude=amplitude, cycles=cycles)
        ov.show_balloon("¡Jeje! Sacudiendo un poquito tu ventana para llamar tu atención, Amo Víctor~ 💫✨", duration_ms=3500)
        return res

    def reach_and_actuate_control(
        self,
        target_x: int,
        target_y: int,
        action: str = "click",
        media_cmd: str = "play-pause",
        scroll_delta: int = -3
    ) -> Dict[str, Any]:
        ik_info = self._apply_ik_hand_reach(target_x, target_y)
        if action == "media":
            act_res = self.actuator.execute_media_control(media_cmd)
        elif action == "scroll":
            self.actuator.inject_pointer_move(target_x, target_y, absolute=True)
            act_res = self.actuator.inject_scroll(scroll_delta)
        else:
            self.actuator.inject_pointer_move(target_x, target_y, absolute=True)
            act_res = self.actuator.inject_pointer_click(0xC0)
        return {"ik": ik_info, "actuation": act_res}

    def click_active_window_action(self, part: str = "center"):
        ov = self.overlay
        ov.wake_up()
        ov.show_balloon("🖱️ Haciendo clic en ventana activa...", duration_ms=2500)
        res = ov.os_interact.click_active_window(part=part)
        ov.show_balloon(res, duration_ms=3000)

    def on_proactive_click(self, tx: int, ty: int, reason: str):
        if self.autonomous_clicks_enabled:
            self.perform_mouse_click(button="left", target_x=tx, target_y=ty, reason=reason)
