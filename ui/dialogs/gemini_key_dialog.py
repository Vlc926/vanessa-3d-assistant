"""
Dialog for configuring Gemini Cloud API key, model selection, and hybrid mode.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtGui import QFont
from core.brain import AssistantBrain


class GeminiApiKeyDialog(QDialog):
    def __init__(self, brain: AssistantBrain, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.setWindowTitle("Configurar IA: Google Gemini & Modo Híbrido")
        self.setFixedSize(500, 320)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; font-weight: 500; }
            QLineEdit, QComboBox {
                background: #1e293b; border: 1px solid #475569; color: white;
                border-radius: 6px; padding: 7px; font-size: 13px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                color: white; border-radius: 8px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #0284c7; }
        """)

        layout = QVBoxLayout(self)
        title = QLabel("🔑 Google Gemini (Versión Actualizada) & Modo Híbrido")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Gemini API Key (Google AI Studio):"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("AIzaSy...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        curr_key = self.brain.settings.get("ai_backend", {}).get("gemini_api_key", "")
        if curr_key:
            self.key_input.setText(curr_key)
        layout.addWidget(self.key_input)

        layout.addWidget(QLabel("Modelo de Gemini Cloud:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItem("gemini-3.5-pro (Flagship - Código, Visión y Razonamiento)", "gemini-3.5-pro")
        self.model_combo.addItem("gemini-3.5-flash (Ultra Rápido y Multimodal)", "gemini-3.5-flash")
        self.model_combo.addItem("gemini-3.5 (Estándar)", "gemini-3.5")
        self.model_combo.addItem("gemini-2.5-pro (Flagship)", "gemini-2.5-pro")
        self.model_combo.addItem("gemini-2.5-flash (Rápido)", "gemini-2.5-flash")
        self.model_combo.addItem("gemini-2.0-flash (Flash)", "gemini-2.0-flash")
        self.model_combo.addItem("gemini-1.5-pro (Estable Pro)", "gemini-1.5-pro")
        self.model_combo.addItem("gemini-1.5-flash (Estable Flash)", "gemini-1.5-flash")

        curr_model = getattr(self.brain, "preferred_model", "gemini-3.5-pro")
        matched = False
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == curr_model:
                self.model_combo.setCurrentIndex(i)
                matched = True
                break
        if not matched and curr_model:
            self.model_combo.setEditText(curr_model)

        lbl_hint = QLabel("💡 Compatible con modelos Gemini 3.5, 2.5 y 2.0. Puedes escribir tu modelo personalizado.")
        lbl_hint.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(self.model_combo)
        layout.addWidget(lbl_hint)

        layout.addWidget(QLabel("Modo de Operación de IA:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔄 Modo Híbrido (Gemini con internet; Local sin conexión)", "hybrid")
        self.mode_combo.addItem("🔒 Solo Modo Local Offline (Privacidad sin internet)", "local_only")
        self.mode_combo.addItem("☁️ Solo Modo Cloud (Siempre Gemini Cloud)", "cloud_only")
        curr_mode = getattr(self.brain, "ai_mode", "hybrid")
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == curr_mode:
                self.mode_combo.setCurrentIndex(i)
                break
        layout.addWidget(self.mode_combo)

        btn_box = QHBoxLayout()
        test_save_btn = QPushButton("Verificar y Guardar")
        test_save_btn.clicked.connect(self.save_and_test)
        btn_box.addWidget(test_save_btn)

        close_btn = QPushButton("Cancelar")
        close_btn.setStyleSheet("background: #334155;")
        close_btn.clicked.connect(self.reject)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

    def save_and_test(self):
        key = self.key_input.text().strip()
        raw_model = self.model_combo.currentData() or self.model_combo.currentText().strip()
        if " (" in raw_model:
            model = raw_model.split(" (")[0].strip()
        else:
            model = raw_model.strip() or "gemini-3.5-pro"

        mode = self.mode_combo.currentData()
        self.brain.set_ai_mode(mode)

        if mode == "local_only":
            QMessageBox.information(self, "Modo Guardado", "Vanessa operará exclusivamente en Modo Local Offline.")
            self.accept()
            return

        if not key:
            if mode == "hybrid":
                QMessageBox.information(self, "Modo Híbrido Activado", "Modo Híbrido activo. Sin API Key, Vanessa responderá con el motor local offline.")
                self.accept()
                return
            QMessageBox.warning(self, "Atención", "Por favor ingresa tu API Key de Gemini.")
            return

        success, msg = self.brain.set_gemini_api_key(key, model)
        if success:
            QMessageBox.information(self, "Conexión Exitosa", f"{msg}\n\nVanessa utilizará {model} cuando haya conexión, e intercalará a Local cuando esté sin conexión.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Validación", f"No se pudo conectar a Google Gemini:\n{msg}")
