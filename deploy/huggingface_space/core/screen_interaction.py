"""
Screen Interaction & Desktop Manipulation Controller for Vanessa.
Handles media button pressing, curious inspection of windows and mouse cursor,
text selection / highlighting via OS shortcuts, and autonomous clicking.
"""
import time
import random
import subprocess
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, QRect
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication


class ScreenInteractor(QObject):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.autonomous_clicks_enabled = False

        self.mouse_tracking_enabled = self.overlay.brain.personality.get("mouse_tracking", True)
        self.mouse_track_timer = QTimer(self)
        self.mouse_track_timer.timeout.connect(self.track_cursor_for_vrm)
        if self.mouse_tracking_enabled:
            self.mouse_track_timer.start(90)

    def track_cursor_for_vrm(self):
        ov = self.overlay
        if not getattr(ov, "using_vrm", False) or not hasattr(ov, "vrm_widget") or not self.mouse_tracking_enabled:
            return
        try:
            out = subprocess.check_output(["hyprctl", "cursorpos"], stderr=subprocess.DEVNULL, text=True)
            parts = [p.strip() for p in out.strip().split(",")]
            if len(parts) == 2:
                cx, cy = float(parts[0]), float(parts[1])
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

    # ------------------------------------------------------------------
    # MUSIC CONTROL WITH THE CASSETTE WALKMAN (in place, no walking)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # MEDIA CONTROL: VIDEO (discreet companion) vs MUSIC (cassette walkman)
    # ------------------------------------------------------------------
    def interactive_press_media(self, action: str = "play_pause", speak: bool = True, media_type: str = "auto"):
        """Differentiates between Video (YouTube / MPV / Streaming) and Music (Spotify / Audio).
        - For MUSIC: Pulls out retro 3D cassette walkman and clicks the button physically.
        - For VIDEO: Smoothly pauses/plays without cassette prop, with a warm anime smile and respectful observation.
        """
        ov = self.overlay
        ov.wake_up()
        a = (action or "play_pause").lower()

        # Detect whether video mode is active
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

        # === VIDEO COMPANION PATH (No cassette prop, respectful polite maid) ===
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
                    ov.vrm_widget.set_expression("happy", 0.9)
                    ov.vrm_widget.play_gesture("nod")

            subprocess.run(cmd, check=False)
            ov.show_balloon(line, duration_ms=3000)
            if speak and hasattr(ov, "tts"):
                ov.tts.speak_async(line, mood="happy" if not want_pause else "relaxed")
            return

        # === MUSIC CASSETTE WALKMAN PATH (Retro prop with physical button press) ===
        if any(k in a for k in ("next", "siguiente", "adelant", "avanzar")):
            gesture, cmd = "cassette_next", ["playerctl", "next"]
            line = random.choice([
                "¡Clic! Siguiente canción, Amo Víctor~ ⏭️🎶",
                "Adelantando la cinta... ¡a ver qué sigue! ⏩✨",
            ])
        elif any(k in a for k in ("prev", "anterior", "retroced", "regres")):
            gesture, cmd = "cassette_prev", ["playerctl", "previous"]
            line = random.choice([
                "Rebobinando un poquito para usted, Amo~ ⏪🎵",
                "¡Clic! Canción anterior, Amo Víctor ⏮️✨",
            ])
        else:
            want_pause = (a in ("pause", "media_pause")) or (a not in ("play", "media_play") and status == "playing")
            if want_pause:
                gesture, cmd = "cassette_pause", ["playerctl", "pause"]
                line = random.choice([
                    "Pausa~ Aquí lo espero cuando quiera continuar, Amo Víctor ⏸️🌸",
                    "¡Clic! La cinta descansa un momento, Amo~ ⏸️",
                    "Pausado. ¿Necesita algo mientras tanto, Amo Víctor? ✨",
                ])
            else:
                gesture, cmd = "cassette_play", ["playerctl", "play"]
                line = random.choice([
                    "¡Y continuamos! Que siga la música, Amo Víctor ▶️🎶",
                    "¡Clic! La cinta vuelve a girar~ ▶️✨",
                    "Reanudando para usted, Amo Víctor 🎧💖",
                ])

        if not (getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget")):
            subprocess.run(cmd, check=False)
            ov.show_balloon(line, duration_ms=3500)
            return

        fired = {"done": False}

        def _execute(*_):
            if fired["done"]:
                return
            fired["done"] = True
            try:
                ov.vrm_widget.gesture_event.disconnect(_on_event)
            except (TypeError, RuntimeError):
                pass
            subprocess.run(cmd, check=False)
            ov.show_balloon(line, duration_ms=3800)
            if speak and hasattr(ov, "tts"):
                ov.tts.speak_async(line, mood="happy")

        def _on_event(g, ev):
            if g == gesture and ev == "press":
                _execute()

        ov.vrm_widget.gesture_event.connect(_on_event)
        ov.vrm_widget.play_gesture(gesture)
        QTimer.singleShot(1900, _execute)  # safety net if the JS event is lost

    # ------------------------------------------------------------------
    # TABS: instant, no walking, just a smile
    # ------------------------------------------------------------------
    def quick_tab_action(self, op: str = "new"):
        ov = self.overlay
        if op == "close":
            ov.os_interact.close_current_tab()
            line = random.choice(["Pestaña cerrada~ 😊", "¡Listo, Amo! Una pestaña menos 😊", "Cerrada 😊✨"])
        else:
            ov.os_interact.open_new_tab()
            line = random.choice(["Nueva pestaña lista, Amo 😊", "¡Aquí tiene su pestaña! 😊", "Abierta 😊✨"])
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            ov.vrm_widget.set_expression("happy", 1.0)
            QTimer.singleShot(1800, lambda: ov.vrm_widget.set_expression("neutral", 1.0))
        ov.show_balloon(line, duration_ms=2200)

    def interactive_click_button(self, action_type: str):
        """
        Analyzes the screen to locate the target button (media play/pause, next track, new tab, etc.),
        walks Vanessa directly to the button location, and plays an adaptive physical gesture
        (stretching upwards, crouching downwards, or direct finger-point) depending on button height,
        then executes the physical click.
        """
        ov = self.overlay
        ov.wake_up()
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        win = ov.os_interact.get_active_window()
        wx = win.get("at", [0, 0])[0] if win and win.get("at") else sw // 4
        wy = win.get("at", [0, 0])[1] if win and win.get("at") else 80
        ww = win.get("size", [900, 600])[0] if win and win.get("size") else 900
        wh = win.get("size", [900, 600])[1] if win and win.get("size") else 600

        act_lower = action_type.lower()
        if "tab" in act_lower:
            self.quick_tab_action("close" if "close" in act_lower else "new")
            return

        # 1. Target Button Screen Coordinates (bx, by)
        if "close" in act_lower and "window" in act_lower:
            # Top-right window close cross 'X'
            button_x = int(wx + ww - 28)
            button_y = int(wy + 22)
            comment = "¡Voy volando a la esquina a cerrar esta ventana, Amo Víctor! ❌✨"
        elif "close" in act_lower and "tab" in act_lower:
            button_x = int(wx + min(320, ww * 0.35))
            button_y = int(wy + 42)
            comment = "¡Voy volando a presionar para cerrar esta pestaña, Amo Víctor! ❌✨"
        elif any(k in act_lower for k in ["new_window", "create_window", "nueva_ventana", "crear_ventana"]):
            # Top bar / workspace launcher area
            button_x = int(sw // 2)
            button_y = 25
            comment = "¡Voy a crear una nueva ventana para ti, Amo Víctor! 🖥️✨"
        elif "tab" in act_lower:
            # Top browser / editor tab bar (e.g. "+" new tab button)
            button_x = int(wx + min(380, ww * 0.42))
            button_y = int(wy + 42)
            comment = "¡Voy volando a presionar el botón de nueva pestaña, Amo Víctor! 📑✨"
        elif any(k in act_lower for k in ["vol_up", "volume_up", "subir_volumen", "mas_volumen"]):
            # Top status bar volume area
            button_x = int(sw - 120)
            button_y = 22
            comment = "¡Voy a subirle el volumen al sistema, Amo Víctor! 🔊✨"
        elif any(k in act_lower for k in ["vol_down", "volume_down", "bajar_volumen", "menos_volumen"]):
            button_x = int(sw - 150)
            button_y = 22
            comment = "¡Voy a bajarle el volumen al sistema, Amo Víctor! 🔉✨"
        elif any(k in act_lower for k in ["next", "siguiente", "adelantar", "adelanta", "avanzar"]):
            # Right media button
            button_x = int(wx + ww // 2 + 65) if ww > 200 else sw // 2 + 65
            button_y = int(wy + wh - 48) if wh > 150 else sh - 65
            comment = "¡Voy a darle al botón de adelantar canción, Amo! ⏭️🎶"
        elif any(k in act_lower for k in ["prev", "anterior", "retroceder", "regresar"]):
            # Left media button
            button_x = int(wx + ww // 2 - 65) if ww > 200 else sw // 2 - 65
            button_y = int(wy + wh - 48) if wh > 150 else sh - 65
            comment = "¡Voy a presionar el botón de canción anterior, Amo Víctor! ⏮️🎵"
        elif any(k in act_lower for k in ["cursor", "mouse", "aqui", "aquí", "click", "clic"]):
            cpos = QCursor.pos()
            button_x = int(cpos.x())
            button_y = int(cpos.y())
            comment = f"¡Voy a dar click en la posición indicada ({button_x}, {button_y}), Amo Víctor! 🎯✨"
        else:
            # Center media play/pause button
            button_x = int(wx + ww // 2) if ww > 200 else sw // 2
            button_y = int(wy + wh - 48) if wh > 150 else sh - 65
            comment = "¡Voy a presionar el botón de reproducir/pausa con mi dedito, Amo! ⏯️✨"

        # 2. Position Vanessa standing conveniently adjacent to the target button
        if button_x + ov.width() + 18 < sw:
            target_x = button_x + 18
        else:
            target_x = max(20, button_x - ov.width() - 18)

        floor_y = sh - ov.height() - 35
        target_y = min(floor_y, max(70, button_y - int(ov.height() * 0.40)))

        def _on_button_arrived():
            # Calculate vertical offset from Vanessa's shoulder/hand level to button Y
            vanessa_hand_y = ov.y() + int(ov.height() * 0.40)
            delta_y = button_y - vanessa_hand_y

            # Adaptive physical animation depending on button height
            if delta_y < -45 or button_y < int(sh * 0.45):
                # Button is HIGH UP (e.g. browser tab bar, top bar, window close) -> Stretch upwards!
                motion_name = "stretch_overhead"
                gaze_y = 0.85
            elif delta_y > 45 or button_y > int(sh * 0.58):
                # Button is LOW DOWN (e.g. bottom media player, taskbar) -> Japanese resting squat!
                motion_name = "japanese_squat"
                gaze_y = -0.85
            else:
                # Button is at MID LEVEL -> Direct forward finger-pointing click!
                motion_name = "point_forward"
                gaze_y = 0.0

            gaze_x = -0.6 if button_x < ov.x() + (ov.width() / 2) else 0.6

            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                ov.vrm_widget.look_at(gaze_x, gaze_y)
                ov.vrm_widget.play_gesture(motion_name)
                ov.vrm_widget.set_expression("happy", 1.0)

            # Move mouse cursor smoothly to exact button coordinate
            ov.os_interact.move_mouse_smooth(button_x, button_y, steps=8)

            # Execute the actual action corresponding to the button
            if "close" in act_lower and "window" in act_lower:
                ov.brain.sys_ctrl.hyprland_dispatch("killactive")
                msg = "¡Ventana cerrada para ti, Amo Víctor! ❌✨"
            elif "close" in act_lower and "tab" in act_lower:
                ov.os_interact.close_current_tab()
                msg = "¡Pestaña cerrada para ti, Amo Víctor! ❌✨"
            elif any(k in act_lower for k in ["new_window", "create_window", "nueva_ventana", "crear_ventana"]):
                ov.brain.sys_ctrl.hyprland_dispatch("exec", "foot")
                msg = "¡Nueva ventana lista para ti, Amo Víctor! 📑🖥️"
            elif "tab" in act_lower:
                ov.os_interact.open_new_tab()
                msg = "¡Aquí tienes tu nueva pestaña, Amo Víctor! 📑✨"
            elif any(k in act_lower for k in ["vol_up", "volume_up", "subir_volumen"]):
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"], check=False)
                msg = "¡Volumen aumentado para ti, Amo Víctor! 🔊🎶"
            elif any(k in act_lower for k in ["vol_down", "volume_down", "bajar_volumen"]):
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"], check=False)
                msg = "¡Volumen reducido, Amo Víctor! 🔉✨"
            elif any(k in act_lower for k in ["next", "siguiente", "adelantar", "adelanta", "avanzar"]):
                subprocess.run(["playerctl", "next"], check=False)
                msg = "¡Siguiente canción lista para ti, Amo Víctor! ⏭️🎶"
            elif any(k in act_lower for k in ["prev", "anterior", "retroceder", "regresar"]):
                subprocess.run(["playerctl", "previous"], check=False)
                msg = "¡Canción anterior lista para ti, Amo Víctor! ⏮️🎵"
            elif any(k in act_lower for k in ["cursor", "mouse", "aqui", "aquí", "click", "clic"]):
                ov.os_interact.click_at(button_x, button_y)
                msg = f"¡Clic ejecutado en ({button_x}, {button_y}), Amo Víctor! 🎯✨"
            else:
                subprocess.run(["playerctl", "play-pause"], check=False)
                msg = "¡Música pausada/reanudada para ti, Amo Víctor! ⏯️💖"

            ov.show_balloon(msg, duration_ms=5000)
            if hasattr(ov, "tts"):
                ov.tts.speak_async(msg, mood="happy")

            QTimer.singleShot(3800, ov.reset_to_idle)

        ov.smooth_roam_to(
            target_x, target_y,
            mode="urgent",
            comment=comment,
            on_arrived=_on_button_arrived
        )

    def curious_inspect_screen(self, target_type: str = "active_window"):
        """Approaches curious element, peers closely, looks directly at it, and points with wonder."""
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
            motion_to_play = "idle_shoot"
        else:
            win = ov.os_interact.get_active_window()
            if win and win.get("at") and win.get("size") and win["size"][0] > 100:
                wx, wy = win["at"]
                ww, wh = win["size"]
                tx = wx + ww + 15
                if tx + ov.width() > sw - 25:
                    tx = max(25, wx - ov.width() - 15)
                    gaze_x = 0.6
                    motion_to_play = "wave_right"
                else:
                    gaze_x = -0.6
                    motion_to_play = "wave_left"
                ty = min(max(75, wy + 20), sh - ov.height() - 35)
                target_title = win.get("title") or win.get("class") or "tu pantalla"
            else:
                tx = sw // 2 - ov.width() // 2
                ty = sh - ov.height() - 50
                gaze_x = 0.0

        # Choose pose: Japanese resting squat if near the bottom, otherwise museum inspection!
        if ty > int(sh * 0.45):
            motion_to_play = "japanese_squat"
        else:
            motion_to_play = "museum_inspect"

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
        """Approaches active window carefully and performs text selection / highlight via OS keys."""
        ov = self.overlay
        ov.wake_up()
        screens = QApplication.screens()
        geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = geom.width()
        sh = geom.height()

        win = ov.os_interact.get_active_window()
        tx = sw - ov.width() - 40
        ty = sh - ov.height() - 45
        if win and win.get("at") and win.get("size"):
            wx, wy = win["at"]
            ww, wh = win["size"]
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
        """Executes mouse click with optional smooth gliding to target coordinates."""
        ov = self.overlay
        ov.wake_up()
        if target_x is not None and target_y is not None:
            if reason:
                ov.show_balloon(f"🖱️ {reason}", duration_ms=3000)
            res = ov.os_interact.click_at(target_x, target_y, button=button, double=double, smooth=True)
        else:
            res = ov.os_interact.click_mouse(button=button, double=double)
        ov.show_balloon(res, duration_ms=3000)

    def click_active_window_action(self, part: str = "center"):
        """Clicks inside the focused window."""
        ov = self.overlay
        ov.wake_up()
        ov.show_balloon("🖱️ Haciendo clic en ventana activa...", duration_ms=2500)
        res = ov.os_interact.click_active_window(part=part)
        ov.show_balloon(res, duration_ms=3000)

    def on_proactive_click(self, tx: int, ty: int, reason: str):
        if self.autonomous_clicks_enabled:
            self.perform_mouse_click(button="left", target_x=tx, target_y=ty, reason=reason)
