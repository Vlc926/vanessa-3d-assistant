"""
Hyprland Multi-Workspace Manager & App Launcher Dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox
)
from PyQt6.QtGui import QFont
from core.os_interact import OSInteractor


class HyprlandWorkspacesDialog(QDialog):
    def __init__(self, os_interact: OSInteractor, parent=None):
        super().__init__(parent)
        self.os_interact = os_interact
        self.setWindowTitle("🖥️ Gestión de Escritorios Hyprland & Aplicaciones")
        self.resize(520, 360)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QPushButton {
                background: #1e293b; color: #38bdf8; border: 1px solid #475569;
                border-radius: 6px; padding: 8px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #38bdf8; color: #0f172a; }
            QComboBox {
                background-color: #1e293b; color: white; border: 1px solid #475569;
                border-radius: 6px; padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("🖥️ Escritorios Múltiples (Hyprland)")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        curr_ws = self.os_interact.get_active_workspace().get("id", 1)
        self.status_lbl = QLabel(f"📍 Escritorio activo actual: <b>{curr_ws}</b>")
        layout.addWidget(self.status_lbl)

        # Workspaces Switcher Row
        layout.addWidget(QLabel("Cambiar de Escritorio:"))
        ws_row = QHBoxLayout()
        for i in range(1, 6):
            btn = QPushButton(f"Espacio {i}")
            if i == curr_ws:
                btn.setStyleSheet("background: #0284c7; color: white; border: 1px solid #38bdf8;")
            btn.clicked.connect(lambda ch, ws=i: self.switch_ws(ws))
            ws_row.addWidget(btn)
        layout.addLayout(ws_row)

        layout.addSpacing(10)
        layout.addWidget(QLabel("🚀 Lanzar Aplicación en Escritorio Específico:"))
        app_row = QHBoxLayout()
        self.app_combo = QComboBox()
        self.app_combo.addItem("🌐 Navegador Firefox", "firefox")
        self.app_combo.addItem("💻 Terminal Kitty", "kitty")
        self.app_combo.addItem("📝 VS Code / Antigravity", "code")
        self.app_combo.addItem("📁 Archivos Dolphin", "dolphin")
        self.app_combo.addItem("🎵 Spotify", "spotify")
        self.app_combo.addItem("🎮 Steam", "steam")
        self.app_combo.addItem("🧮 Calculadora", "kcalc")
        app_row.addWidget(self.app_combo)

        self.target_ws_combo = QComboBox()
        for i in range(1, 6):
            self.target_ws_combo.addItem(f"En Escritorio {i}", i)
        app_row.addWidget(self.target_ws_combo)

        launch_btn = QPushButton("Lanzar")
        launch_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8); color: white;")
        launch_btn.clicked.connect(self.do_launch)
        app_row.addWidget(launch_btn)
        layout.addLayout(app_row)

        layout.addSpacing(10)
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background: #334155; color: white;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def switch_ws(self, ws: int):
        self.os_interact.switch_workspace(ws)
        self.status_lbl.setText(f"📍 Escritorio activo actual: <b>{ws}</b>")

    def do_launch(self):
        app = self.app_combo.currentData()
        ws = self.target_ws_combo.currentData()
        self.os_interact.launch_app(app, workspace_id=ws)
        self.accept()
