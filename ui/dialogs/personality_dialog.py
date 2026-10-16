"""
Dialog for configuring Vanessa appearance, models (Live2D/VRM/sprites), and anime voice settings.
"""
import threading
import asyncio
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTextEdit, QPushButton, QMessageBox
)
from PyQt6.QtGui import QFont
from core.brain import AssistantBrain
from core.anime_tts import ANIME_VOICE_PRESETS


class PersonalityConfigDialog(QDialog):
    def __init__(self, brain: AssistantBrain, overlay, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.overlay = overlay
        self.setWindowTitle("Aspecto, Modelos Live2D/VRM y Voz Anime")
        self.setFixedSize(580, 560)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; font-weight: 500; }
            QLineEdit, QComboBox, QTextEdit {
                background: #1e293b; border: 1px solid #475569; color: white;
                border-radius: 6px; padding: 7px; font-size: 13px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a855f7, stop:1 #ec4899);
                color: white; border-radius: 8px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #9333ea; }
        """)

        layout = QVBoxLayout(self)
        title = QLabel("🎭 Aspecto, Modelos Live2D y Voz Anime de Vanessa")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #f472b6;")
        layout.addWidget(title)

        # Name & Title
        row1 = QHBoxLayout()
        row1_lbl = QVBoxLayout()
        row1_lbl.addWidget(QLabel("Nombre:"))
        self.name_edit = QLineEdit(self.brain.personality.get("name", "Vanessa"))
        row1_lbl.addWidget(self.name_edit)
        row1.addLayout(row1_lbl)

        row2_lbl = QVBoxLayout()
        row2_lbl.addWidget(QLabel("Título:"))
        self.title_edit = QLineEdit(self.brain.personality.get("title", "Tu Asistente Maid Personal"))
        row2_lbl.addWidget(self.title_edit)
        row1.addLayout(row2_lbl)
        layout.addLayout(row1)

        # Character Model Selection (Live2D & Sprites)
        layout.addWidget(QLabel("Modelo de Animación en Pantalla:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("🌟 Live2D: Hiyori (Anime Maid / Flagship - Físicas y Expresiones)", "live2d:hiyori")
        self.model_combo.addItem("🌟 Live2D: Haru (Schoolgirl - 27 Animaciones Completas)", "live2d:haru")
        self.model_combo.addItem("🌟 Live2D: Mao (Chibi Tierna con Expresiones)", "live2d:mao")
        self.model_combo.addItem("🌟 Live2D: Rice (Maid Gatita Neko Chibi)", "live2d:rice")
        self.model_combo.addItem("🎨 Sprite 2D: Hu Tao (Genshin Shimeji 46 frames)", "sprite:hutao")
        self.model_combo.addItem("🎨 Sprite 2D: Kamisato Ayaka (Genshin Shimeji 46 frames)", "sprite:ayaka")
        self.model_combo.addItem("🎨 Sprite 2D: Hatsune Miku (Vocaloid Shimeji 46 frames)", "sprite:miku")

        # Select current model
        if getattr(self.overlay, "using_live2d", True):
            current_val = f"live2d:{getattr(self.overlay, 'current_live2d_model', 'hiyori')}"
        else:
            current_val = f"sprite:{self.overlay.current_theme}"

        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == current_val:
                self.model_combo.setCurrentIndex(i)
                break
        layout.addWidget(self.model_combo)

        # Open models folder button
        models_folder_btn = QPushButton("📂 Abrir Carpeta de Modelos (VRM 3D & Live2D)")
        models_folder_btn.setStyleSheet("background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8;")
        models_folder_btn.clicked.connect(self.overlay.open_models_folder)
        layout.addWidget(models_folder_btn)

        # Voice selection
        layout.addWidget(QLabel("Voz Anime de Vanessa (Edge-TTS Anime / VOICEVOX):"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItem("🌸 Dalia Anime (Español Latino Dulce, Viva y Expresiva)", "dalia_anime")
        self.voice_combo.addItem("🎌 Nanami Anime (Waifu Japonesa Original)", "nanami_anime")
        self.voice_combo.addItem("✨ Elvira Anime (Tsundere Española Enérgica)", "elvira_anime")
        self.voice_combo.addItem("🎀 Salomé Anime (Melódica Suave y Cálida)", "salome_anime")
        self.voice_combo.addItem("🤖 VOICEVOX (Motor Local de VTubing / Zundamon)", "voicevox")

        curr_voice = self.brain.personality.get("voice_settings", {}).get("preset", "dalia_anime")
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == curr_voice:
                self.voice_combo.setCurrentIndex(i)
                break
        layout.addWidget(self.voice_combo)

        # Speech Style & System Prompt
        layout.addWidget(QLabel("Directriz de Personalidad (Prompt Adaptativo):"))
        self.style_edit = QTextEdit()
        self.style_edit.setPlainText(self.brain.personality.get("speech_style", ""))
        self.style_edit.setMaximumHeight(80)
        layout.addWidget(self.style_edit)

        # Buttons
        btn_box = QHBoxLayout()
        test_voice_btn = QPushButton("🎵 Probar Voz Anime")
        test_voice_btn.setStyleSheet("background: #334155; color: #38bdf8;")
        test_voice_btn.clicked.connect(self.test_voice)
        btn_box.addWidget(test_voice_btn)

        save_btn = QPushButton("💾 Guardar Configuración")
        save_btn.clicked.connect(self.save_personality)
        btn_box.addWidget(save_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background: #1e293b;")
        close_btn.clicked.connect(self.reject)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

    def test_voice(self):
        preset_key = self.voice_combo.currentData()
        name = self.name_edit.text().strip() or "Vanessa"
        if preset_key == "voicevox":
            self.overlay.tts.provider = "voicevox"
        else:
            self.overlay.tts.provider = "edge_tts"
            self.overlay.tts.set_preset(preset_key)

        phrase = f"A su completo servicio, Amo Víctor. Soy {name}, ¡ahora con mi voz anime mejorada para ti!"
        threading.Thread(target=lambda: asyncio.run(self.overlay.tts.speak(phrase, mood="happy")), daemon=True).start()

    def save_personality(self):
        new_name = self.name_edit.text().strip() or "Vanessa"
        new_title = self.title_edit.text().strip()
        model_choice = self.model_combo.currentData()
        voice_choice = self.voice_combo.currentData()
        new_style = self.style_edit.toPlainText().strip()

        mode, model_id = model_choice.split(":")

        updated_dict = {
            "name": new_name,
            "title": new_title,
            "speech_style": new_style,
            "avatar_type": mode,
            "theme": model_id if mode == "sprite" else self.overlay.current_theme,
            "live2d_model": model_id if mode == "live2d" else getattr(self.overlay, "current_live2d_model", "hiyori"),
            "voice_settings": {
                "preset": voice_choice,
                "online_voice": ANIME_VOICE_PRESETS.get(voice_choice, {}).get("voice", "es-MX-DaliaNeural")
            }
        }
        self.brain.update_personality(updated_dict)

        if voice_choice == "voicevox":
            self.overlay.tts.provider = "voicevox"
        else:
            self.overlay.tts.provider = "edge_tts"
            self.overlay.tts.set_preset(voice_choice)

        if mode == "live2d":
            self.overlay.switch_live2d_model(model_id)
        else:
            self.overlay.switch_theme(model_id)

        QMessageBox.information(
            self, "Guardado Exitoso",
            f"¡Modelo {model_id} y voz anime aplicados con éxito!\nVanessa está lista y reaccionando a tu entorno."
        )
        self.accept()
