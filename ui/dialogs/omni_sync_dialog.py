import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QFrame, QTabWidget, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from core.platform_verifier import PlatformVerifier
class OmniSyncDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verifier = PlatformVerifier()
        self.setWindowTitle("🔗 Sincronización y Verificación de Cuentas - Vanessa")
        self.setFixedSize(620, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        head_box = QVBoxLayout()
        title_lbl = QLabel("🌸 Sincronización y Verificación por Plataforma")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff75a0;")
        head_box.addWidget(title_lbl)
        sub_lbl = QLabel("Ingresa y verifica individualmente tus credenciales en cada plataforma mediante sus APIs oficiales.")
        sub_lbl.setStyleSheet("color: #d8b4fe; font-size: 12px;")
        head_box.addWidget(sub_lbl)
        layout.addLayout(head_box)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tab_steam = self._create_platform_tab("steam", "🎮 Steam", "Usuario, SteamID o URL personalizada:", "Contraseña o Clave de cuenta:")
        self.tab_spotify = self._create_platform_tab("spotify", "🎵 Spotify", "Correo o Nombre de usuario de Spotify:", "Contraseña o Token:")
        self.tab_discord = self._create_platform_tab("discord", "💬 Discord", "Usuario de Discord (@usuario) o Token:", "Contraseña o PIN:")
        self.tab_telegram = self._create_platform_tab("telegram", "✈️ Telegram", "@Usuario o Número de teléfono:", "Bot Token o Clave:")
        self.tab_whatsapp = self._create_platform_tab("whatsapp", "📱 WhatsApp", "Número con código de país (Ej: +521...):", "PIN o Contraseña:")
        self.tabs.addTab(self.tab_steam, "🎮 Steam")
        self.tabs.addTab(self.tab_spotify, "🎵 Spotify")
        self.tabs.addTab(self.tab_discord, "💬 Discord")
        self.tabs.addTab(self.tab_telegram, "✈️ Telegram")
        self.tabs.addTab(self.tab_whatsapp, "📱 WhatsApp")
        bottom_box = QHBoxLayout()
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("font-size: 12px; color: #c084fc; font-weight: 600;")
        bottom_box.addWidget(self.summary_lbl)
        bottom_box.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("class", "secondary-btn")
        btn_close.clicked.connect(self.close)
        bottom_box.addWidget(btn_close)
        layout.addLayout(bottom_box)
        self._update_all_cards()
    def _create_platform_tab(self, platform_key: str, display_name: str, user_label: str, pass_label: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        lbl_user = QLabel(user_label)
        lbl_user.setStyleSheet("font-weight: 600; color: #fdf2f8;")
        layout.addWidget(lbl_user)
        txt_user = QLineEdit()
        txt_user.setPlaceholderText("Ingresa tu cuenta...")
        layout.addWidget(txt_user)
        lbl_pass = QLabel(pass_label)
        lbl_pass.setStyleSheet("font-weight: 600; color: #fdf2f8;")
        layout.addWidget(lbl_pass)
        txt_pass = QLineEdit()
        txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        txt_pass.setPlaceholderText("••••••••")
        layout.addWidget(txt_pass)
        btn_verify = QPushButton(f"🔍 Verificar Información de {display_name.split()[1]}")
        btn_verify.setProperty("class", "primary-btn")
        btn_verify.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_verify)
        status_card = QFrame()
        status_card.setProperty("class", "status-card")
        card_layout = QVBoxLayout(status_card)
        card_layout.setSpacing(6)
        status_header = QHBoxLayout()
        badge_lbl = QLabel("⚪ No vinculado")
        badge_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #94a3b8;")
        status_header.addWidget(badge_lbl)
        status_header.addStretch()
        btn_disconnect = QPushButton("Desvincular")
        btn_disconnect.setProperty("class", "danger-btn")
        btn_disconnect.setVisible(False)
        status_header.addWidget(btn_disconnect)
        card_layout.addLayout(status_header)
        details_lbl = QLabel("Ingresa tu información arriba y haz clic en verificar para conectar esta cuenta.")
        details_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1;")
        details_lbl.setWordWrap(True)
        card_layout.addWidget(details_lbl)
        layout.addWidget(status_card)
        layout.addStretch()
        btn_verify.clicked.connect(lambda: self._trigger_verification(platform_key, txt_user, txt_pass, btn_verify, badge_lbl, details_lbl, btn_disconnect))
        btn_disconnect.clicked.connect(lambda: self._disconnect(platform_key, txt_user, txt_pass, badge_lbl, details_lbl, btn_disconnect))
        widget.ref_txt_user = txt_user
        widget.ref_txt_pass = txt_pass
        widget.ref_btn_verify = btn_verify
        widget.ref_badge_lbl = badge_lbl
        widget.ref_details_lbl = details_lbl
        widget.ref_btn_disconnect = btn_disconnect
        return widget
    def _trigger_verification(self, platform_key: str, txt_user: QLineEdit, txt_pass: QLineEdit, btn_verify: QPushButton, badge_lbl: QLabel, details_lbl: QLabel, btn_disconnect: QPushButton):
        val_user = txt_user.text().strip()
        val_pass = txt_pass.text().strip()
        if not val_user:
            details_lbl.setText("⚠️ Por favor ingresa el usuario o correo de la cuenta.")
            details_lbl.setStyleSheet("color: #f87171; font-size: 11px;")
            return
        btn_verify.setEnabled(False)
        badge_lbl.setText("⏳ Verificando información con API...")
        badge_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        details_lbl.setText("Conectando con los servidores oficiales de la plataforma...")
        details_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        QTimer.singleShot(100, lambda: self._execute_verification(platform_key, val_user, val_pass, btn_verify, badge_lbl, details_lbl, btn_disconnect))
    def _execute_verification(self, platform_key: str, val_user: str, val_pass: str, btn_verify: QPushButton, badge_lbl: QLabel, details_lbl: QLabel, btn_disconnect: QPushButton):
        btn_verify.setEnabled(True)
        if platform_key == "steam":
            ok, msg, info = self.verifier.verify_steam(val_user, val_pass)
        elif platform_key == "spotify":
            ok, msg, info = self.verifier.verify_spotify(val_user, val_pass)
        elif platform_key == "discord":
            ok, msg, info = self.verifier.verify_discord(val_user, val_pass)
        elif platform_key == "telegram":
            ok, msg, info = self.verifier.verify_telegram(val_user, val_pass)
        elif platform_key == "whatsapp":
            ok, msg, info = self.verifier.verify_whatsapp(val_user, val_pass)
        else:
            ok, msg, info = False, "Plataforma no reconocida", {}
        if ok:
            badge_lbl.setText("🟢 Verificado y Sincronizado")
            badge_lbl.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 13px;")
            details_lbl.setText(f"✅ {msg}")
            details_lbl.setStyleSheet("color: #86efac; font-size: 11px;")
            btn_disconnect.setVisible(True)
        else:
            badge_lbl.setText("❌ Error de Verificación")
            badge_lbl.setStyleSheet("color: #f87171; font-weight: bold; font-size: 13px;")
            details_lbl.setText(f"⚠️ {msg}")
            details_lbl.setStyleSheet("color: #fca5a5; font-size: 11px;")
        self._update_summary()
    def _disconnect(self, platform_key: str, txt_user: QLineEdit, txt_pass: QLineEdit, badge_lbl: QLabel, details_lbl: QLabel, btn_disconnect: QPushButton):
        self.verifier.disconnect_platform(platform_key)
        txt_user.clear()
        txt_pass.clear()
        badge_lbl.setText("⚪ No vinculado")
        badge_lbl.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
        details_lbl.setText("Cuenta desvinculada. Ingresa tus datos para volver a verificar.")
        details_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        btn_disconnect.setVisible(False)
        self._update_summary()
    def _update_all_cards(self):
        tab_mapping = {
            "steam": self.tab_steam,
            "spotify": self.tab_spotify,
            "discord": self.tab_discord,
            "telegram": self.tab_telegram,
            "whatsapp": self.tab_whatsapp
        }
        for key, tab_widget in tab_mapping.items():
            acc = self.verifier.accounts.get(key, {})
            if acc.get("verified"):
                tab_widget.ref_txt_user.setText(acc.get("user", ""))
                tab_widget.ref_badge_lbl.setText(f"🟢 Verificado ({acc.get('status', 'Activo')})")
                tab_widget.ref_badge_lbl.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 13px;")
                tab_widget.ref_details_lbl.setText(f"✅ Cuenta verificada: {acc.get('user', '')} - {acc.get('details', '')}")
                tab_widget.ref_details_lbl.setStyleSheet("color: #86efac; font-size: 11px;")
                tab_widget.ref_btn_disconnect.setVisible(True)
            else:
                tab_widget.ref_badge_lbl.setText("⚪ No vinculado")
                tab_widget.ref_badge_lbl.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
                tab_widget.ref_details_lbl.setText("Ingresa tu información y haz clic en verificar para conectar esta cuenta.")
                tab_widget.ref_details_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
                tab_widget.ref_btn_disconnect.setVisible(False)
        self._update_summary()
    def _update_summary(self):
        count = sum(1 for a in self.verifier.accounts.values() if a.get("verified"))
        total = len(self.verifier.accounts)
        self.summary_lbl.setText(f"✨ Cuentas verificadas y activas: {count} de {total}")
