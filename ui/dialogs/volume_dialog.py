"""
Independent Voice Volume Controller Dialog.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class VolumeDialog(QDialog):
    def __init__(self, current_vol: int, on_volume_changed_callback, parent=None):
        super().__init__(parent)
        self.on_volume_changed = on_volume_changed_callback
        self.setWindowTitle("🔊 Volumen Independiente de Vanessa")
        self.resize(420, 220)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QSlider::groove:horizontal { height: 8px; background: #1e293b; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #ec4899); border-radius: 4px; }
            QSlider::handle:horizontal { background: #f8fafc; border: 2px solid #ec4899; width: 18px; margin: -5px 0; border-radius: 9px; }
            QPushButton {
                background: #1e293b; color: #38bdf8; border: 1px solid #475569;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #38bdf8; color: #0f172a; }
        """)

        layout = QVBoxLayout(self)
        title = QLabel("🔊 Control de Volumen de Vanessa (Independiente)")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(title)

        desc = QLabel("Este control modifica <b>únicamente la voz de Vanessa</b> sin alterar el volumen general de tu sistema.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(desc)

        self.val_label = QLabel(f"Nivel actual: <b>{current_vol}%</b>")
        self.val_label.setStyleSheet("color: #ec4899; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.val_label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(5, 100)
        self.slider.setValue(current_vol)
        self.slider.valueChanged.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.slider)

        preset_row = QHBoxLayout()
        for p in [20, 40, 65, 85, 100]:
            btn = QPushButton(f"{p}%")
            btn.clicked.connect(lambda ch, val=p: self.set_preset(val))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        close_btn = QPushButton("Listo")
        close_btn.setStyleSheet("background: #0284c7; color: white;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _on_slider_moved(self, val: int):
        self.val_label.setText(f"Nivel actual: <b>{val}%</b>")

    def _on_slider_released(self):
        val = self.slider.value()
        self.on_volume_changed(val)

    def set_preset(self, val: int):
        self.slider.setValue(val)
        self.on_volume_changed(val)
