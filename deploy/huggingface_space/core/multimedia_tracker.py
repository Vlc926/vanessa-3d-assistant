"""
Multimedia Tracking, Music Sync & YouTube Video Watching Engine for Vanessa.
Monitors MPRIS metadata (Spotify, YouTube, browser, VLC, MPV) and PipeWire/PulseAudio.
Classifies music genres (Rock, Sad/Melancholy/Lofi, Pop, Electronic, Chill) and provides
adaptive choreography and glows.
Includes YouTube video companion mode: sits next to player, reacts live, inquires when paused,
and autonomously walks over to unpause if Amo Víctor does not respond!
"""
import time
import subprocess
import random
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, QTimer


class MultimediaTracker(QObject):
    def __init__(self, overlay, poll_interval_ms: int = 1800):
        super().__init__(overlay)
        self.overlay = overlay
        self.current_media_playing = False
        self.current_media_track = ""
        self.current_player_name = ""
        self.current_genre = "pop"
        self.is_video_mode = False
        self.last_media_dialogue_time = 0.0
        self.last_video_reaction_time = 0.0
        self.video_watch_start_time = 0.0

        self.media_monitor_timer = QTimer(self)
        self.media_monitor_timer.timeout.connect(self.check_multimedia_status)
        self.media_monitor_timer.start(poll_interval_ms)

    def cancel_auto_resume(self):
        """No-op: autonomous video unpause is permanently disabled for discreet companion mode."""
        pass

    def classify_music_genre(self, track_info: str) -> str:
        """Classifies music into distinct genres to drive custom animations and headphone colors."""
        lower = track_info.lower()
        if any(k in lower for k in ["rock", "metal", "heavy", "slipknot", "linkin park", "metallica", "ac/dc", "queen", "rammstein", "nirvana", "guitar", "punk", "disturbed", "iron maiden"]):
            return "rock"
        elif any(k in lower for k in ["sad", "slow", "cry", "lonely", "acoustic", "piano", "lofi", "chill", "tears", "ballad", "triste", "nostalgia", "soledad", "llanto", "depressed"]):
            return "sad"
        elif any(k in lower for k in ["pop", "dance", "j-pop", "k-pop", "bts", "blackpink", "vocaloid", "miku", "cute", "happy", "yoasobi", "ado", "dua lipa", "taylor", "ariana"]):
            return "pop"
        elif any(k in lower for k in ["edm", "techno", "house", "phonk", "synth", "cyberpunk", "trance", "bass", "dubstep", "remix", "electronic"]):
            return "electronic"
        return "chill"

    def check_multimedia_status(self):
        ov = self.overlay
        if not getattr(ov, "using_vrm", False) or not hasattr(ov, "vrm_widget"):
            return

        try:
            # 1. Primary: playerctl MPRIS metadata
            res = subprocess.run(
                ["playerctl", "metadata", "--format", "{{status}}|{{playerName}}|{{artist}}|{{title}}"],
                capture_output=True, text=True, timeout=0.8
            )
            is_playing = False
            player_name = ""
            track_info = ""
            if res.returncode == 0 and res.stdout.strip():
                line = res.stdout.strip().split("\n")[0]
                parts = line.split("|")
                if parts and parts[0].strip().lower() == "playing":
                    is_playing = True
                    player_name = parts[1].strip() if len(parts) > 1 else ""
                    artist = parts[2].strip() if len(parts) > 2 else ""
                    title = parts[3].strip() if len(parts) > 3 else ""
                    track_info = f"{artist} - {title}".strip(" -")
                elif parts and parts[0].strip().lower() == "paused":
                    player_name = parts[1].strip() if len(parts) > 1 else ""
                    artist = parts[2].strip() if len(parts) > 2 else ""
                    title = parts[3].strip() if len(parts) > 3 else ""
                    track_info = f"{artist} - {title}".strip(" -")

            # 2. Secondary: PipeWire / PulseAudio active sound detection
            if not is_playing and not track_info:
                pactl_res = subprocess.run(
                    ["pactl", "list", "sink-inputs"],
                    capture_output=True, text=True, timeout=0.8
                )
                if pactl_res.returncode == 0 and "Sink Input #" in pactl_res.stdout:
                    blocks = pactl_res.stdout.split("Sink Input #")
                    for b in blocks[1:]:
                        if "Corked: no" in b or 'pulse.corked = "false"' in b:
                            if 'application.name = "paplay"' not in b and 'application.process.binary = "pacat"' not in b:
                                is_playing = True
                                app_name = "Audio de PC"
                                for bline in b.splitlines():
                                    if "application.name =" in bline:
                                        app_name = bline.split("=")[-1].strip(' "\t')
                                        break
                                track_info = f"Contenido en {app_name}"
                                player_name = app_name
                                break

            # Determine whether this is a YouTube / multimedia video or music
            active_win = ov.os_interact.get_active_window() if hasattr(ov, "os_interact") else {}
            win_title = active_win.get("title", "")
            win_class = active_win.get("class", "").lower()

            is_video = (
                "youtube" in track_info.lower() or
                "youtube" in win_title.lower() or
                "youtube" in player_name.lower() or
                win_class in ("mpv", "vlc", "totem", "celluloid")
            )

            now = time.time()

            # Handle Video Mode Transitions
            if is_playing and is_video:
                self._handle_video_playing(active_win, track_info, now)
                return

            # Handle Music Mode Transitions
            if is_playing and not is_video:
                self._handle_music_playing(track_info, now)
                return

            # Handle Paused / Stopped State
            if not is_playing:
                if self.is_video_mode:
                    self._handle_video_paused(now)
                else:
                    self._handle_music_stopped()

        except Exception as e:
            pass

    def _handle_music_playing(self, track_info: str, now: float):
        ov = self.overlay
        genre = self.classify_music_genre(track_info)

        if not self.current_media_playing or self.is_video_mode or track_info != self.current_media_track:
            self.current_media_playing = True
            self.is_video_mode = False
            self.current_media_track = track_info
            self.current_genre = genre
            self.cancel_auto_resume()

            # Genre-specific choreography & lighting
            if genre == "rock":
                bpm = 155.0
                ov.vrm_widget.set_music_active(True, bpm)
                ov.vrm_widget.set_music_genre("rock", bpm)
                ov.vrm_widget.start_motion("happy_gesture")
                msg = random.choice([
                    f"¡Uff, Amo Víctor! ¡Este rock está potentísimo! 🎸🔥 ¡Mire cómo disfruto la energía!",
                    f"¡Qué temazo tan pesado y con vibra brutal, Amo Víctor! 🤘⚡ ¡Vamos con todo!"
                ])
            elif genre == "sad":
                bpm = 72.0
                ov.vrm_widget.set_music_active(True, bpm)
                ov.vrm_widget.set_music_genre("sad", bpm)
                ov.vrm_widget.play_gesture("look_around_curious")
                ov.vrm_widget.set_expression("relaxed", 0.9)
                msg = random.choice([
                    f"Esta canción es tan melancólica y profunda, Amo Víctor... me da un poquito de nostalgia. 🌧️💙 Déjeme acompañarlo en silencio a su ladito.",
                    f"Un tema muy reflexivo y emotivo... si necesita un respiro o un café calientito, aquí estoy con usted, Amo. ☕✨"
                ])
            elif genre == "electronic":
                bpm = 135.0
                ov.vrm_widget.set_music_active(True, bpm)
                ov.vrm_widget.set_music_genre("electronic", bpm)
                ov.vrm_widget.start_motion("clapping")
                msg = random.choice([
                    f"¡Menudos graves tiene este beat, Amo Víctor! 🎧⚡ ¡Parece que estamos en el futuro!",
                    f"¡El ritmo electrónico está increíble! 🪩✨ ¡Sintiendo los bajos, Amo!"
                ])
            elif genre == "pop":
                bpm = 128.0
                ov.vrm_widget.set_music_active(True, bpm)
                ov.vrm_widget.set_music_genre("pop", bpm)
                ov.vrm_widget.start_motion("peace")
                msg = random.choice([
                    f"¡Kyaa! ¡Amo Víctor, este ritmo pop es súper contagioso y alegre! 💖✨ ¡No me puedo quedar quieta!",
                    f"¡Qué melodía tan bonita, Amo! '{track_info}' 🎶🌸 ¡Vamos a disfrutarla juntitos!"
                ])
            else:
                bpm = 100.0
                ov.vrm_widget.set_music_active(True, bpm)
                ov.vrm_widget.set_music_genre("chill", bpm)
                ov.vrm_widget.start_motion("cat_pose")
                msg = f"¡Disfrutando de la música junto a usted, Amo Víctor! '{track_info}' 🎵✨"

            if now - self.last_media_dialogue_time > 60.0:
                self.last_media_dialogue_time = now
                ov.show_balloon(msg, duration_ms=4500)
                if hasattr(ov, "tts"):
                    ov.tts.speak_async(msg, mood="happy" if genre != "sad" else "relaxed")

    def _handle_music_stopped(self):
        ov = self.overlay
        if self.current_media_playing or getattr(ov, "_music_was_active", False):
            self.current_media_playing = False
            ov._music_was_active = False
            ov.vrm_widget.set_music_active(False)
            print("[Multimedia] Música finalizada o pausada. Vanessa regresando a postura natural.")

    def _handle_video_playing(self, active_win: dict, track_info: str, now: float):
        ov = self.overlay
        self.cancel_auto_resume()

        # Entering Video Companion Watching Mode
        if not self.is_video_mode:
            self.is_video_mode = True
            self.current_media_playing = True
            self.video_watch_start_time = now
            self.last_video_reaction_time = now

            # Turn off music headphones during video
            ov.vrm_widget.set_music_active(False)

            # Move near the video player window and sit down to watch together!
            wx = active_win.get("at", [0, 0])[0] if active_win.get("at") else 200
            wy = active_win.get("at", [0, 0])[1] if active_win.get("at") else 100
            ww = active_win.get("size", [900, 600])[0] if active_win.get("size") else 900
            wh = active_win.get("size", [900, 600])[1] if active_win.get("size") else 600

            # Target position: Bottom right edge of the video window
            target_x = max(20, min(wx + ww - ov.width() + 40, 1920 - ov.width() - 35))
            target_y = max(60, min(wy + wh - ov.height() + 80, 1200 - ov.height() - 35))

            def _on_video_arrived():
                # Look towards the center of the video screen!
                video_center_x = (wx + ww / 2 - ov.x()) / 400.0
                video_center_y = (wy + wh / 2 - ov.y()) / 400.0
                # Stand attentively and curiously next to video window with Amo Víctor
                ov.vrm_widget.play_gesture("museum_inspect")
                ov.vrm_widget.set_expression("relaxed", 0.8)

            intro_msg = "Disfrute de su video, Amo Víctor. Aquí me quedo en silencio acompañándolo 👀🍿"
            ov.smooth_roam_to(
                target_x, target_y,
                mode="urgent",
                comment=intro_msg,
                on_arrived=_on_video_arrived
            )
            ov.show_balloon(intro_msg, duration_ms=3500)
            return

        # Quiet Anime Companion Etiquette:
        # Vanessa stays silently attentive next to the window while Amo watches,
        # enjoying the video with subtle expressions without spamming dialogue balloons!
        if now - self.last_video_reaction_time > 18.0:
            self.last_video_reaction_time = now
            subtle_expressions = ["relaxed", "happy", "surprised"]
            ov.vrm_widget.set_expression(random.choice(subtle_expressions), 0.6)

    def _handle_video_paused(self, now: float):
        ov = self.overlay
        self.is_video_mode = False
        self.current_media_playing = False

        # Look at Amo Víctor with polite attentiveness
        ov.vrm_widget.look_at(0.0, 0.6)
        ov.vrm_widget.set_expression("relaxed", 0.8)

        # Do NOT hijack video with unsolicited dialogue loops or auto-unpausing.
        # Vanessa waits respectfully for Amo's next command.
        print("[Multimedia] Video pausado por el Amo Víctor. Vanessa permanece atenta sin interrumpir.")
