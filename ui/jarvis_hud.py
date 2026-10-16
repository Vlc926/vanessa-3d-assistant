"""
Jarvis Cyber Holographic HUD & Diagnostic Dashboard for Vanessa.
Provides a futuristic Iron Man / Cyber-Maid overlay dashboard with:
- Real-time CPU, RAM, Disk, and Battery animated telemetry
- Network diagnostics (Public IP, ping latency)
- Active reminders queue & countdown timers
- One-click Iron Man Protocol execution (Trabajo, Descanso, Multimedia, Diagnóstico)
- Biometric security and audio status cards
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class JarvisCyberHUDDialog(QDialog):
    def __init__(self, jarvis_engine, overlay, parent=None):
        super().__init__(parent or overlay)
        self.jarvis = jarvis_engine
        self.overlay = overlay

        self.setWindowTitle("⚡ JARVIS CYBER HUD • Panel Holográfico de Vanessa")
        self.setFixedSize(720, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(10, 15, 29, 245);
                border: 2px solid rgba(56, 189, 248, 200);
                border-radius: 16px;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel { color: #f8fafc; font-size: 13px; }
            QProgressBar {
                border: 1px solid rgba(56, 189, 248, 120);
                border-radius: 6px;
                text-align: center;
                color: white;
                background: rgba(30, 41, 59, 180);
                height: 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                border-radius: 5px;
            }
            QPushButton {
                background: rgba(30, 41, 59, 220);
                color: #38bdf8;
                border: 1.5px solid rgba(56, 189, 248, 140);
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(56, 189, 248, 220), stop:1 rgba(129, 140, 248, 220));
                color: #ffffff;
                border-color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 1. Header Holographic Banner
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("⚡ J.A.R.V.I.S. CYBER HUD")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; letter-spacing: 2px;")
        subtitle = QLabel("● Sistema Operativo Vanessa 3D • Amo: Víctor • Enlace Activo")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        btn_close = QPushButton("✕ Cerrar HUD")
        btn_close.setFixedSize(110, 32)
        btn_close.setStyleSheet("background: rgba(239, 68, 68, 180); color: white; border: none;")
        btn_close.clicked.connect(self.accept)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # 2. Protocol Actions Quick Launch Row (Iron Man Protocols)
        proto_box = QHBoxLayout()
        proto_box.setSpacing(8)

        btn_work = QPushButton("🚀 Protocolo Trabajo")
        btn_work.setToolTip("Abre entorno de desarrollo en Workspace 1")
        btn_work.clicked.connect(lambda: self._trigger_protocol("trabajo"))
        proto_box.addWidget(btn_work)

        btn_sleep = QPushButton("🌙 Protocolo Descanso")
        btn_sleep.setToolTip("Pausa música, baja volumen y activa modo reposo")
        btn_sleep.clicked.connect(lambda: self._trigger_protocol("descanso"))
        proto_box.addWidget(btn_sleep)

        btn_media = QPushButton("🎵 Protocolo Fiesta")
        btn_media.setToolTip("Abre música, sube volumen y activa baile 3D")
        btn_media.clicked.connect(lambda: self._trigger_protocol("multimedia"))
        proto_box.addWidget(btn_media)

        btn_diag = QPushButton("🛡️ Diagnóstico Total")
        btn_diag.setToolTip("Escaneo profundo de sistema y red")
        btn_diag.clicked.connect(lambda: self._trigger_protocol("diagnostico"))
        proto_box.addWidget(btn_diag)

        layout.addLayout(proto_box)

        # 3. Main Telemetry Cards (2 Columns)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        # Left Column: Hardware & System
        left_card = QFrame()
        left_card.setStyleSheet("background: rgba(15, 23, 42, 200); border: 1px solid rgba(56, 189, 248, 80); border-radius: 12px; padding: 10px;")
        left_v = QVBoxLayout(left_card)
        left_v.setSpacing(8)

        card_title1 = QLabel("💻 RECURSOS DE HARDWARE")
        card_title1.setStyleSheet("color: #818cf8; font-weight: bold; font-size: 12px;")
        left_v.addWidget(card_title1)

        # CPU
        self.lbl_cpu = QLabel("CPU Load: 0%")
        self.prog_cpu = QProgressBar()
        left_v.addWidget(self.lbl_cpu)
        left_v.addWidget(self.prog_cpu)

        # RAM
        self.lbl_ram = QLabel("Memoria RAM: 0GB / 0GB")
        self.prog_ram = QProgressBar()
        left_v.addWidget(self.lbl_ram)
        left_v.addWidget(self.prog_ram)

        # Disk
        self.lbl_disk = QLabel("Disco (/): 0GB")
        self.prog_disk = QProgressBar()
        left_v.addWidget(self.lbl_disk)
        left_v.addWidget(self.prog_disk)

        # Battery & Uptime
        self.lbl_battery = QLabel("🔋 Batería: --")
        self.lbl_uptime = QLabel("⏱️ Uptime: --")
        left_v.addWidget(self.lbl_battery)
        left_v.addWidget(self.lbl_uptime)
        left_v.addStretch()

        cards_layout.addWidget(left_card)

        # Right Column: Network & Jarvis Reminders
        right_card = QFrame()
        right_card.setStyleSheet("background: rgba(15, 23, 42, 200); border: 1px solid rgba(56, 189, 248, 80); border-radius: 12px; padding: 10px;")
        right_v = QVBoxLayout(right_card)
        right_v.setSpacing(8)

        card_title2 = QLabel("🌐 RED & AGENDA ACTIVA DE JARVIS")
        card_title2.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        right_v.addWidget(card_title2)

        self.lbl_net = QLabel("📡 Red: Comprobando...")
        self.lbl_ip = QLabel("🌐 IP Pública: --")
        right_v.addWidget(self.lbl_net)
        right_v.addWidget(self.lbl_ip)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("border-color: rgba(56, 189, 248, 60);")
        right_v.addWidget(div)

        rem_title = QLabel("⏰ Recordatorios y Temporizadores Pendientes:")
        rem_title.setStyleSheet("font-weight: bold; color: #f472b6; font-size: 11px;")
        right_v.addWidget(rem_title)

        self.lbl_reminders = QLabel("Sin recordatorios pendientes.")
        self.lbl_reminders.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.lbl_reminders.setWordWrap(True)
        right_v.addWidget(self.lbl_reminders)
        right_v.addStretch()

        cards_layout.addWidget(right_card)
        layout.addLayout(cards_layout)

        # 4. Status Bar at Bottom
        self.status_bar = QLabel("Estado: HUD sincronizado en tiempo real.")
        self.status_bar.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.status_bar)

        # Update telemetry every 1.5 seconds
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_telemetry)
        self.update_timer.start(1500)
        self.refresh_telemetry()

    def _trigger_protocol(self, proto: str):
        res = self.jarvis.execute_protocol(proto, overlay=self.overlay)
        msg = res.get("message", res.get("error", ""))
        self.status_bar.setText(f"Protocolo '{proto}': {msg[:70]}...")
        if self.overlay:
            self.overlay.show_balloon(msg, duration_ms=4500)

    def refresh_telemetry(self):
        tel = self.overlay.os_interact.get_system_telemetry()
        if "error" not in tel:
            cpu = tel.get("cpu_percent", 0.0)
            self.lbl_cpu.setText(f"CPU: {cpu}% ({tel.get('cpu_cores', 4)} núcleos)")
            self.prog_cpu.setValue(int(cpu))

            ram_used = tel.get("ram_used_gb", 0.0)
            ram_tot = tel.get("ram_total_gb", 0.0)
            ram_pct = tel.get("ram_percent", 0.0)
            self.lbl_ram.setText(f"RAM: {ram_used}GB / {ram_tot}GB ({ram_pct}%)")
            self.prog_ram.setValue(int(ram_pct))

            disk_pct = tel.get("disk_percent", 0.0)
            self.lbl_disk.setText(f"Disco (/): {tel.get('disk_used_gb', 0)}GB / {tel.get('disk_total_gb', 0)}GB ({disk_pct}%)")
            self.prog_disk.setValue(int(disk_pct))

            self.lbl_battery.setText(f"🔋 Batería: {tel.get('battery', 'N/A')}")
            self.lbl_uptime.setText(f"⏱️ Uptime: {tel.get('uptime', 'N/A')} | {tel.get('processes_count', 0)} procesos")

        # Network check
        net = self.jarvis.get_network_diagnostics()
        self.lbl_net.setText(f"📡 Estado: {net.get('status')} ({net.get('latency_ms') or '?'}ms)")
        self.lbl_ip.setText(f"🌐 IP Pública: {net.get('public_ip')}")

        # Reminders check
        rems = self.jarvis.get_pending_reminders()
        if rems:
            lines = [f"• «{r['text']}» (en {r['remaining_str']})" for r in rems[:3]]
            self.lbl_reminders.setText("\n".join(lines))
        else:
            self.lbl_reminders.setText("No hay recordatorios activos.")
