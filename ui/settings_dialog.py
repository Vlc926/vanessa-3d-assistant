import sys
import os
import json
import sqlite3
import time
import threading
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSlider, QCheckBox, QPushButton, QLineEdit, QTextEdit,
    QProgressBar, QGroupBox, QFrame, QMessageBox, QApplication, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QRect, QPoint
from PyQt6.QtGui import QFont, QColor

_CACHED_INPUT_DEVICES = None

def get_audio_input_devices():
    global _CACHED_INPUT_DEVICES
    if _CACHED_INPUT_DEVICES is not None:
        return _CACHED_INPUT_DEVICES
    devs = []
    if sd:
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get('max_input_channels', 0) > 0:
                    name = dev.get('name', f'Dispositivo {idx}')
                    devs.append((idx, name))
        except Exception:
            pass
    _CACHED_INPUT_DEVICES = devs
    return devs


class AudioTesterWorker(QObject):
    finished_signal = pyqtSignal(str, float, float, float)  
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, stt, voice_mgr, device_idx=None, gain=1.8, duration=3.2):
        super().__init__()
        self.stt = stt
        self.voice_mgr = voice_mgr
        self.device_idx = device_idx
        self.gain = gain
        self.duration = duration

    def run_test(self):
        if not sd:
            self.error_signal.emit("sounddevice no disponible.")
            return

        try:
            sample_rate = 16000
            actual_sr = 16000
            chunk_size = 1600  
            stream = None

            try:
                stream = sd.InputStream(
                    device=self.device_idx,
                    samplerate=sample_rate,
                    channels=1,
                    dtype='int16',
                    blocksize=chunk_size
                )
            except Exception:
                try:
                    dev_info = sd.query_devices(self.device_idx)
                    actual_sr = int(dev_info.get('default_samplerate', 48000))
                    chunk_size = int(actual_sr * 0.1)
                    stream = sd.InputStream(
                        device=self.device_idx,
                        samplerate=actual_sr,
                        channels=1,
                        dtype='int16',
                        blocksize=chunk_size
                    )
                except Exception:
                    actual_sr = 16000
                    chunk_size = 1600
                    stream = sd.InputStream(
                        samplerate=actual_sr,
                        channels=1,
                        dtype='int16',
                        blocksize=chunk_size
                    )

            total_samples = int(self.duration * actual_sr)
            collected = []
            
            with stream:
                steps = max(1, int(total_samples / chunk_size))
                for step in range(steps):
                    data, _ = stream.read(chunk_size)
                    collected.append(data.flatten())
                    pct = int(((step + 1) / steps) * 100)
                    self.progress_signal.emit(pct)

            audio = np.concatenate(collected)
            if actual_sr != 16000 and len(audio) > 0:
                target_len = int(len(audio) * 16000 / actual_sr)
                indices = np.linspace(0, len(audio) - 1, target_len)
                audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.int16)

            floats = audio.astype(np.float32) * self.gain
            amplified = np.clip(floats, -32768, 32767).astype(np.int16)

            peak = float(np.max(np.abs(amplified)))
            rms = float(np.sqrt(np.mean(amplified.astype(np.float32)**2)))

            text = "(No se detectaron palabras legibles)"
            if self.stt and len(amplified) > sample_rate * 0.4:
                try:
                    res = self.stt.transcribe_audio_array(amplified, sample_rate)
                    if res and len(res.strip()) > 0:
                        text = res.strip()
                except Exception as e:
                    text = f"(Error STT: {e})"

            sim = 100.0
            if self.voice_mgr:
                try:
                    _, s, _, _ = self.voice_mgr.verify_speaker(amplified, name="Amo Víctor")
                    sim = s
                except Exception:
                    sim = 100.0

            self.finished_signal.emit(text, peak, rms, sim)

        except Exception as e:
            self.error_signal.emit(str(e))


class VanessaSettingsDialog(QDialog):
    settings_saved_signal = pyqtSignal()
    _devices_ready_signal = pyqtSignal(object, object)  

    def __init__(self, brain, overlay, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.overlay = overlay
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("⚙️ Centro de Ajustes y Calibración de Vanessa")
        self.resize(760, 720)
        self.setMinimumSize(740, 680)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background: #0f172a;
                border-radius: 8px;
                padding: 10px;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #94a3b8;
                padding: 10px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 600;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #0f172a;
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 14px;
                padding: 16px 14px 14px 14px;
                font-weight: bold;
                color: #38bdf8;
                font-size: 13px;
                background-color: rgba(15, 23, 42, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                background-color: #0f172a;
                color: #38bdf8;
                border-radius: 3px;
            }
            QLabel {
                color: #f1f5f9;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 1.5px solid #475569;
                color: #ffffff;
                border-radius: 6px;
                padding: 4px 10px;
                min-height: 38px;
                max-height: 42px;
                font-size: 13px;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1.5px solid #38bdf8;
                background-color: #0f172a;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e293b;
                border: 1.5px solid #475569;
                color: #ffffff;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QTextEdit:focus {
                border: 1.5px solid #38bdf8;
                background-color: #0f172a;
                color: #ffffff;
            }
            QComboBox {
                background-color: #1e293b;
                border: 1.5px solid #475569;
                color: #ffffff;
                border-radius: 6px;
                padding: 4px 10px;
                min-height: 38px;
                max-height: 42px;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 1.5px solid #38bdf8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #334155;
            }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #38bdf8;
                width: 0px;
                height: 0px;
                margin-right: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                border: 1px solid #38bdf8;
                color: #ffffff;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                padding: 6px;
            }
            QWidget#tabContentWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #0f172a;
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QSlider {
                min-height: 26px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #334155;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #38bdf8;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QCheckBox {
                color: #f1f5f9;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background: #1e293b;
            }
            QCheckBox::indicator:checked {
                background: #38bdf8;
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #6366f1);
                color: #ffffff;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #38bdf8;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
                color: #ffffff;
            }
            QPushButton#secondaryBtn {
                background: #1e293b;
                border: 1px solid #475569;
                color: #cbd5e1;
            }
            QPushButton#secondaryBtn:hover {
                background: #334155;
                color: #ffffff;
                border-color: #64748b;
            }
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #f8fafc;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        header_title = QLabel("⚙️ Centro de Ajustes y Calibración de Vanessa")
        header_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")
        header.addWidget(header_title)
        header.addStretch()
        root_layout.addLayout(header)

        self.tabs = QTabWidget(self)
        root_layout.addWidget(self.tabs)

        self.init_voice_tab()
        self.init_avatar_tab()
        self.init_tts_tab()
        self.init_ai_tab()

        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.clicked.connect(self.reject)
        bottom_bar.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("💾 Guardar y Aplicar Cambios")
        self.save_btn.clicked.connect(self.save_all_settings)
        bottom_bar.addWidget(self.save_btn)

        root_layout.addLayout(bottom_bar)

        self.connect_live_vu()

    def showEvent(self, event):
        super().showEvent(event)
        self.adjust_reciprocal_position()

    def adjust_reciprocal_position(self):
        try:
            screens = QApplication.screens()
            screen = screens[0] if screens else None
            screen_geom = screen.geometry() if screen else QRect(0, 0, 1920, 1200)
            sw = screen_geom.width()
            sh = screen_geom.height()

            dw = self.width()
            dh = self.height()

            v_pos = self.overlay.get_current_screen_pos() if hasattr(self.overlay, "get_current_screen_pos") else self.overlay.pos()
            vx = v_pos.x()
            vy = v_pos.y()
            vw = self.overlay.width()
            vh = self.overlay.height()

            if (vx + (vw // 2)) > (sw // 2):
                target_x = max(25, vx - dw - 25)
            else:
                target_x = min(sw - dw - 25, vx + vw + 25)

            target_y = max(35, min(sh - dh - 40, vy + (vh - dh) // 2))

            self.move(target_x, target_y)

            def _dispatch_hypr():
                try:
                    import subprocess
                    subprocess.run(
                        ["hyprctl", "dispatch", "movewindowpixel", f"exact {target_x} {target_y},title:^.*Ajustes.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                    subprocess.run(
                        ["hyprctl", "dispatch", "pin", "title:^.*Ajustes.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                    subprocess.run(
                        ["hyprctl", "dispatch", "alterzorder", "top,title:^.*Ajustes.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                except Exception:
                    pass

            QTimer.singleShot(60, _dispatch_hypr)
        except Exception as e:
            print(f"[SettingsDialog] Error adjust_reciprocal_position: {e}")

    def _wrap_tab_scroll(self, content_widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        scroll.viewport().setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content_widget)
        return scroll

    def init_voice_tab(self):
        tab = QWidget()
        tab.setObjectName("tabContentWidget")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 14, 10)
        layout.setSpacing(12)

        dev_group = QGroupBox("🎙️ Dispositivo de Entrada de Micrófono")
        dev_layout = QVBoxLayout(dev_group)
        
        self.dev_combo = QComboBox()
        self.dev_list = []
        
        saved_dev = self.brain.personality.get("audio_calibration", {}).get("device_index", None)
        self._devices_ready_signal.connect(self._apply_audio_devices)
        global _CACHED_INPUT_DEVICES
        if _CACHED_INPUT_DEVICES is not None:
            self._apply_audio_devices(_CACHED_INPUT_DEVICES, saved_dev)
        else:
            self.dev_combo.addItem("Predeterminado del Sistema (PipeWire / ALSA)", None)
            threading.Thread(
                target=self._async_fetch_audio_devices,
                args=(saved_dev,),
                daemon=True
            ).start()

        dev_layout.addWidget(self.dev_combo)
        layout.addWidget(dev_group)

        vu_group = QGroupBox("📊 Nivel de Entrada en Tiempo Real (VU-Metro)")
        vu_layout = QVBoxLayout(vu_group)

        vu_header = QHBoxLayout()
        vu_header.addWidget(QLabel("Volumen Actual:"))
        self.vu_status_lbl = QLabel("🔴 Silencio")
        self.vu_status_lbl.setStyleSheet("font-weight: bold; color: #94a3b8;")
        vu_header.addStretch()
        vu_header.addWidget(self.vu_status_lbl)
        vu_layout.addLayout(vu_header)

        self.vu_bar = QProgressBar()
        self.vu_bar.setRange(0, 100)
        self.vu_bar.setValue(0)
        self.vu_bar.setTextVisible(False)
        self.vu_bar.setFixedHeight(16)
        self.vu_bar.setStyleSheet("""
            QProgressBar {
                background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:0.7 #f59e0b, stop:0.95 #ef4444);
                border-radius: 7px;
            }
        """)
        vu_layout.addWidget(self.vu_bar)
        layout.addWidget(vu_group)

        sens_group = QGroupBox("🎚️ Sensibilidad y Ganancia Digital (Pre-amplificación)")
        sens_layout = QVBoxLayout(sens_group)
        sens_layout.setSpacing(10)
        sens_layout.setContentsMargins(14, 16, 14, 16)

        calib = self.brain.personality.get("audio_calibration", {})
        gain_row = QHBoxLayout()
        gain_lbl = QLabel("Ganancia de Micrófono (Mic Boost):")
        gain_lbl.setMinimumHeight(22)
        gain_row.addWidget(gain_lbl)
        self.gain_val_lbl = QLabel(f"x{calib.get('mic_gain', 1.8):.1f}")
        self.gain_val_lbl.setMinimumHeight(22)
        self.gain_val_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
        gain_row.addStretch()
        gain_row.addWidget(self.gain_val_lbl)
        sens_layout.addLayout(gain_row)

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(5, 40)  
        self.gain_slider.setValue(int(calib.get("mic_gain", 1.8) * 10))
        self.gain_slider.valueChanged.connect(lambda v: self.gain_val_lbl.setText(f"x{v/10.0:.1f}"))
        sens_layout.addWidget(self.gain_slider)
        sens_layout.addSpacing(6)

        vad_row = QHBoxLayout()
        vad_lbl = QLabel("Sensibilidad de Detección (VAD):")
        vad_lbl.setMinimumHeight(22)
        vad_row.addWidget(vad_lbl)
        sens_val = calib.get("vad_sensitivity", 0.85)
        self.sens_val_lbl = QLabel("Alta (Susurros y voz suave)" if sens_val >= 0.75 else "Normal")
        self.sens_val_lbl.setMinimumHeight(22)
        self.sens_val_lbl.setStyleSheet("font-weight: bold; color: #f472b6;")
        vad_row.addStretch()
        vad_row.addWidget(self.sens_val_lbl)
        sens_layout.addLayout(vad_row)

        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 3)  
        curr_sens_step = 1 if sens_val >= 0.75 else (2 if sens_val >= 0.4 else 3)
        self.sens_slider.setValue(curr_sens_step)
        def _on_sens_change(val):
            labels = {1: "Alta (Susurros y voz suave)", 2: "Normal (Uso habitual)", 3: "Filtrado Agresivo de Ruido"}
            self.sens_val_lbl.setText(labels.get(val, "Normal"))
        self.sens_slider.valueChanged.connect(_on_sens_change)
        sens_layout.addWidget(self.sens_slider)
        sens_layout.addSpacing(6)

        sil_row = QHBoxLayout()
        sil_lbl = QLabel("Pausa de Silencio para Responder:")
        sil_lbl.setMinimumHeight(22)
        sil_row.addWidget(sil_lbl)
        sil_ms = calib.get("silence_timeout_ms", 750)
        self.sil_val_lbl = QLabel(f"{sil_ms} ms")
        self.sil_val_lbl.setMinimumHeight(22)
        self.sil_val_lbl.setStyleSheet("font-weight: bold; color: #a855f7;")
        sil_row.addStretch()
        sil_row.addWidget(self.sil_val_lbl)
        sens_layout.addLayout(sil_row)

        self.sil_slider = QSlider(Qt.Orientation.Horizontal)
        self.sil_slider.setRange(400, 1500)
        self.sil_slider.setSingleStep(50)
        self.sil_slider.setValue(sil_ms)
        self.sil_slider.valueChanged.connect(lambda v: self.sil_val_lbl.setText(f"{v} ms"))
        sens_layout.addWidget(self.sil_slider)

        layout.addWidget(sens_group)

        test_group = QGroupBox("🧪 Prueba de Micrófono && Transcripción en Vivo")
        test_layout = QVBoxLayout(test_group)

        test_btn_row = QHBoxLayout()
        self.test_mic_btn = QPushButton("🎙️ Grabar 3s y Probar Transcripción")
        self.test_mic_btn.clicked.connect(self.start_mic_test)
        test_btn_row.addWidget(self.test_mic_btn)
        test_layout.addLayout(test_btn_row)

        self.test_progress = QProgressBar()
        self.test_progress.setRange(0, 100)
        self.test_progress.setValue(0)
        self.test_progress.setFixedHeight(8)
        self.test_progress.setTextVisible(False)
        self.test_progress.hide()
        test_layout.addWidget(self.test_progress)

        self.test_result_lbl = QLabel("Presione el botón para hablar y calibrar su voz.")
        self.test_result_lbl.setStyleSheet("color: #cbd5e1; font-style: italic;")
        self.test_result_lbl.setWordWrap(True)
        test_layout.addWidget(self.test_result_lbl)

        layout.addWidget(test_group)
        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_scroll(tab), "🎙️ Audio y Voz")

    def _apply_audio_devices(self, devs, saved_dev):
        try:
            self.dev_combo.count()
        except RuntimeError:
            return  
        self.dev_combo.clear()
        self.dev_list = devs
        for idx, name in devs:
            self.dev_combo.addItem(f"[{idx}] {name}", idx)
        if self.dev_combo.count() == 0:
            self.dev_combo.addItem("Predeterminado del Sistema (PipeWire / ALSA)", None)
        
        if saved_dev is not None:
            for i in range(self.dev_combo.count()):
                if self.dev_combo.itemData(i) == saved_dev:
                    self.dev_combo.setCurrentIndex(i)
                    break

    def _async_fetch_audio_devices(self, saved_dev):
        devs = get_audio_input_devices()
        try:
            self._devices_ready_signal.emit(devs, saved_dev)
        except RuntimeError:
            pass


    def init_avatar_tab(self):
        tab = QWidget()
        tab.setObjectName("tabContentWidget")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 14, 10)
        layout.setSpacing(12)

        mod_group = QGroupBox("✨ Modelo de Compañera en Pantalla")
        mod_layout = QVBoxLayout(mod_group)

        self.model_combo = QComboBox()
        model_labels = {
            "vanessa": "✨ 3D VRM: Vanessa (Flagship Anime Oficial)",
            "kira": "⚡ 3D VRM: Kira (Urban Streetwear Anime - ZZZ Style)",
            "aoi": "🌸 3D VRM: Aoi (Cyberpunk Stylized Anime)",
            "kuro": "🔮 3D VRM: Kuro (Goth Cyber Anime)",
            "orion": "🌌 3D VRM: Orion (Sci-Fi High-Detail Anime)",
        }
        vrm_map = getattr(self.overlay, "vrm_models_map", {})
        for m_key in vrm_map.keys():
            label = model_labels.get(m_key, f"✨ 3D VRM: {m_key.capitalize()} (Personalizado)")
            self.model_combo.addItem(label, f"vrm:{m_key}")

        curr_vrm = getattr(self.overlay, "current_vrm_model", "vanessa")
        curr_val = f"vrm:{curr_vrm}"
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == curr_val:
                self.model_combo.setCurrentIndex(i)
                break
        mod_layout.addWidget(self.model_combo)

        open_folder_btn = QPushButton("📂 Abrir Carpeta de Modelos (VRM && Live2D)")
        open_folder_btn.setObjectName("secondaryBtn")
        if self.overlay and hasattr(self.overlay, "open_models_folder"):
            open_folder_btn.clicked.connect(self.overlay.open_models_folder)
        mod_layout.addWidget(open_folder_btn)
        layout.addWidget(mod_group)

        anima_group = QGroupBox("🎮 Dinámicas de Vida Estilo AniMA Engine")
        anima_layout = QVBoxLayout(anima_group)

        p = self.brain.personality
        self.chk_mouse_track = QCheckBox("👀 Seguimiento Inteligente de Mirada y Cuello al Ratón (Cursor Tracking)")
        self.chk_mouse_track.setChecked(p.get("mouse_tracking", True))
        anima_layout.addWidget(self.chk_mouse_track)

        self.chk_saccades = QCheckBox("👁️ Micro-movimientos Oculares Vivos (Saccades) y Parpadeo Doble")
        self.chk_saccades.setChecked(p.get("eye_saccades", True))
        anima_layout.addWidget(self.chk_saccades)

        self.chk_breathing = QCheckBox("🌬️ Dinámica de Respiración en Pecho y Hombros (Breathing Physics)")
        self.chk_breathing.setChecked(p.get("breathing_physics", True))
        anima_layout.addWidget(self.chk_breathing)

        self.chk_head_pat = QCheckBox("❤️ Reacción Tierna a Caricias al hacer Clic en la Cabecita (Head Patting)")
        self.chk_head_pat.setChecked(p.get("head_patting", True))
        anima_layout.addWidget(self.chk_head_pat)

        self.chk_music = QCheckBox("🎵 Percepción de Música en Reproducción (Spotify / Reproductor)")
        self.chk_music.setChecked(p.get("music_perception", True))
        anima_layout.addWidget(self.chk_music)

        layout.addWidget(anima_group)
        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_scroll(tab), "🌟 Avatar 3D && Físicas")

    def init_tts_tab(self):
        tab = QWidget()
        tab.setObjectName("tabContentWidget")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 14, 10)
        layout.setSpacing(12)

        voice_group = QGroupBox("🗣️ Motor de Síntesis de Voz Anime")
        voice_layout = QVBoxLayout(voice_group)
        voice_layout.setSpacing(10)
        voice_layout.setContentsMargins(14, 16, 14, 16)

        self.tts_combo = QComboBox()
        self.tts_combo.addItem("💖 Gaby AI Conversational (ElevenLabs Oficial - Dulce y Juvenil)", "gaby_elevenlabs")
        self.tts_combo.addItem("🌸 Vanessa Dalia (Dulce, Cálida y Ultra-Natural - Flagship)", "dalia_anime")
        self.tts_combo.addItem("✨ Paloma Anime (Alegre, Chispeante y Juvenil)", "paloma_anime")
        self.tts_combo.addItem("🎀 Salomé Maid (Suave, Atenta y Melódica)", "salome_anime")
        self.tts_combo.addItem("👑 Elvira Noble (Elegante, Serena y Expresiva)", "elvira_anime")
        self.tts_combo.addItem("💫 Catalina Dulce (Tierno Tono Anime Juvenil)", "catalina_anime")
        self.tts_combo.addItem("🌸 Kokoro-82M (Respaldo Local Sin Conexión)", "kokoro_anime")
        self.tts_combo.addItem("🤗 Hugging Face API: Facebook MMS Spanish (Servidor Remoto)", "hf_anime")

        curr_preset = self.brain.personality.get("voice_settings", {}).get("online_voice", self.brain.settings.get("voice_settings", {}).get("voice", "gaby_elevenlabs"))
        for i in range(self.tts_combo.count()):
            if self.tts_combo.itemData(i) == curr_preset:
                self.tts_combo.setCurrentIndex(i)
                break
        voice_layout.addWidget(self.tts_combo)

        eleven_row = QHBoxLayout()
        eleven_row.addWidget(QLabel("Clave API ElevenLabs (Opcional):"))
        saved_eleven_key = self.brain.settings.get("voice_settings", {}).get("elevenlabs_api_key", os.environ.get("ELEVENLABS_API_KEY", ""))
        self.eleven_key_edit = QLineEdit(saved_eleven_key)
        self.eleven_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        eleven_row.addWidget(self.eleven_key_edit)
        show_eleven_btn = QPushButton("👁️")
        show_eleven_btn.setFixedWidth(40)
        show_eleven_btn.clicked.connect(lambda: self.eleven_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if self.eleven_key_edit.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password
        ))
        eleven_row.addWidget(show_eleven_btn)
        voice_layout.addLayout(eleven_row)
        layout.addWidget(voice_group)

        vol_group = QGroupBox("🔊 Control de Volumen Independiente de Vanessa")
        vol_layout = QVBoxLayout(vol_group)
        vol_layout.setSpacing(10)
        vol_layout.setContentsMargins(14, 16, 14, 16)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Nivel de Volumen:"))
        curr_vol = getattr(self.overlay, "vanessa_volume", 85)
        self.vol_val_lbl = QLabel(f"{curr_vol}%")
        self.vol_val_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
        vol_row.addStretch()
        vol_row.addWidget(self.vol_val_lbl)
        vol_layout.addLayout(vol_row)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(5, 100)
        self.vol_slider.setValue(curr_vol)
        def _on_vol_drag(v):
            self.vol_val_lbl.setText(f"{v}%")
            if self.overlay and hasattr(self.overlay, "tts"):
                self.overlay.tts.set_volume(v)

        def _on_vol_release():
            if self.overlay and hasattr(self.overlay, "set_volume"):
                self.overlay.set_volume(self.vol_slider.value())

        self.vol_slider.valueChanged.connect(_on_vol_drag)
        self.vol_slider.sliderReleased.connect(_on_vol_release)
        vol_layout.addWidget(self.vol_slider)

        test_tts_btn = QPushButton("🎵 Probar Voz Anime Ahora")
        test_tts_btn.clicked.connect(self.test_tts_voice)
        vol_layout.addWidget(test_tts_btn)
        layout.addWidget(vol_group)

        chatter_group = QGroupBox("💬 Opciones de Interacción Conversacional")
        chatter_layout = QVBoxLayout(chatter_group)
        chatter_layout.setSpacing(10)
        chatter_layout.setContentsMargins(14, 16, 14, 16)

        self.chk_ambient_voice = QCheckBox("Permitir comentarios ambientales espontáneos solo por voz (sin burbuja)")
        self.chk_ambient_voice.setChecked(self.brain.personality.get("ambient_voice_only", True))
        chatter_layout.addWidget(self.chk_ambient_voice)

        layout.addWidget(chatter_group)
        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_scroll(tab), "🔊 Voz Anime y Volumen")

    def init_ai_tab(self):
        tab = QWidget()
        tab.setObjectName("tabContentWidget")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 14, 10)
        layout.setSpacing(12)

        id_group = QGroupBox("👤 Identidad y Título de Vanessa")
        id_layout = QVBoxLayout(id_group)
        id_layout.setSpacing(10)
        id_layout.setContentsMargins(14, 16, 14, 16)

        row = QHBoxLayout()
        r1 = QVBoxLayout()
        r1.addWidget(QLabel("Nombre:"))
        self.name_edit = QLineEdit(self.brain.personality.get("name", "Vanessa"))
        r1.addWidget(self.name_edit)
        row.addLayout(r1)

        r2 = QVBoxLayout()
        r2.addWidget(QLabel("Título:"))
        self.title_edit = QLineEdit(self.brain.personality.get("title", "Tu Asistente Maid Personal & Traviesa"))
        r2.addWidget(self.title_edit)
        row.addLayout(r2)
        id_layout.addLayout(row)
        layout.addWidget(id_group)

        ai_group = QGroupBox("🔑 Google Gemini AI (Cloud && Modo Híbrido)")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(10)
        ai_layout.setContentsMargins(14, 16, 14, 16)

        ai_layout.addWidget(QLabel("Gemini API Key (Google AI Studio):"))
        key_row = QHBoxLayout()
        self.key_edit = QLineEdit(self.brain.gemini_api_key or "")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self.key_edit)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setFixedWidth(40)
        show_key_btn.clicked.connect(lambda: self.key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if self.key_edit.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password
        ))
        key_row.addWidget(show_key_btn)
        ai_layout.addLayout(key_row)

        ai_layout.addWidget(QLabel("Modelo Preferido de Gemini:"))
        self.model_ai_combo = QComboBox()
        self.model_ai_combo.addItem("gemini-3.5-flash (Ultra Rápido y Capaz - Recomendado)", "gemini-3.5-flash")
        self.model_ai_combo.addItem("gemini-2.5-flash (Estable de Alto Rendimiento)", "gemini-2.5-flash")
        self.model_ai_combo.addItem("gemini-1.5-flash (Económico)", "gemini-1.5-flash")
        
        saved_m = self.brain.preferred_model
        for i in range(self.model_ai_combo.count()):
            if self.model_ai_combo.itemData(i) == saved_m:
                self.model_ai_combo.setCurrentIndex(i)
                break
        ai_layout.addWidget(self.model_ai_combo)
        layout.addWidget(ai_group)

        default_p = {}
        try:
            with open("config/personality.json", "r", encoding="utf-8") as f:
                default_p = json.load(f)
        except Exception:
            pass
        sys_prompt_val = self.brain.personality.get("system_prompt") or default_p.get("system_prompt", "")
        speech_style_val = self.brain.personality.get("speech_style") or default_p.get("speech_style", "")

        sys_group = QGroupBox("🧠 Prompt Principal del Sistema (Directriz de Identidad)")
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setSpacing(8)
        sys_layout.setContentsMargins(14, 16, 14, 16)
        self.sys_prompt_edit = QTextEdit()
        self.sys_prompt_edit.setPlainText(sys_prompt_val)
        self.sys_prompt_edit.setMinimumHeight(95)
        self.sys_prompt_edit.setMaximumHeight(130)
        sys_layout.addWidget(self.sys_prompt_edit)
        layout.addWidget(sys_group)

        style_group = QGroupBox("💬 Estilo de Voz, Tono y Expresión")
        style_layout = QVBoxLayout(style_group)
        style_layout.setSpacing(8)
        style_layout.setContentsMargins(14, 16, 14, 16)
        self.style_edit = QTextEdit()
        self.style_edit.setPlainText(speech_style_val)
        self.style_edit.setMinimumHeight(75)
        self.style_edit.setMaximumHeight(105)
        style_layout.addWidget(self.style_edit)
        layout.addWidget(style_group)

        layout.addStretch()
        self.tabs.addTab(self._wrap_tab_scroll(tab), "🧠 IA && Personalidad")

    def connect_live_vu(self):
        worker = getattr(self.overlay, "voice_worker", None)
        if worker and hasattr(worker, "listener") and worker.listener:
            self._vu_source = worker.listener.level_signal
            self._vu_source.connect(self.update_vu_meter)
            self.destroyed.connect(self._disconnect_live_vu)
            self.finished.connect(self._disconnect_live_vu)

    def _disconnect_live_vu(self, *_):
        src = getattr(self, "_vu_source", None)
        if src is not None:
            try:
                src.disconnect(self.update_vu_meter)
            except (TypeError, RuntimeError):
                pass
            self._vu_source = None

    def update_vu_meter(self, level: float, is_voice: bool):
        try:
            if not self.isVisible() or not hasattr(self, "vu_bar"):
                return
            val = int(min(100, max(0, level)))
            self.vu_bar.setValue(val)
        except RuntimeError:
            self._disconnect_live_vu()
            return
        if is_voice:
            self.vu_status_lbl.setText("🟢 Voz Detectada (Hablando)")
            self.vu_status_lbl.setStyleSheet("font-weight: bold; color: #10b981;")
        else:
            self.vu_status_lbl.setText("🔴 Silencio")
            self.vu_status_lbl.setStyleSheet("font-weight: bold; color: #94a3b8;")

    def start_mic_test(self):
        self.test_mic_btn.setEnabled(False)
        self.test_progress.setValue(0)
        self.test_progress.show()
        self.test_result_lbl.setText("🎙️ ¡Hable ahora con voz normal!... Grabando 3 segundos...")
        self.test_result_lbl.setStyleSheet("color: #38bdf8; font-weight: bold;")

        dev_idx = self.dev_combo.currentData()
        gain = self.gain_slider.value() / 10.0

        self.tester_thread = QThread()
        self.tester_worker = AudioTesterWorker(
            self.overlay.stt, self.overlay.voice_mgr,
            device_idx=dev_idx, gain=gain, duration=3.0
        )
        self.tester_worker.moveToThread(self.tester_thread)
        self.tester_thread.started.connect(self.tester_worker.run_test)
        self.tester_worker.progress_signal.connect(self.test_progress.setValue)
        self.tester_worker.finished_signal.connect(self.on_mic_test_finished)
        self.tester_worker.error_signal.connect(self.on_mic_test_error)
        self.tester_thread.start()

    def on_mic_test_finished(self, text, peak, rms, sim):
        self.test_mic_btn.setEnabled(True)
        self.test_progress.hide()
        self.tester_thread.quit()
        self.tester_thread.wait(1500)

        status_color = "#10b981" if len(text) > 0 and not text.startswith("(") else "#f59e0b"
        self.test_result_lbl.setText(
            f"✨ Transcrito: \"{text}\"\n"
            f"📊 Nivel RMS: {rms:.1f} (Pico: {peak:.0f}) | Coincidencia de voz: {sim:.0f}%"
        )
        self.test_result_lbl.setStyleSheet(f"color: {status_color}; font-weight: 500;")

    def on_mic_test_error(self, err):
        self.test_mic_btn.setEnabled(True)
        self.test_progress.hide()
        self.tester_thread.quit()
        self.tester_thread.wait(1500)
        self.test_result_lbl.setText(f"❌ Error en prueba: {err}")
        self.test_result_lbl.setStyleSheet("color: #ef4444; font-weight: 500;")

    def test_tts_voice(self):
        chosen_voice = self.tts_combo.currentData()
        if hasattr(self, "eleven_key_edit"):
            e_key = self.eleven_key_edit.text().strip()
            if e_key:
                os.environ["ELEVENLABS_API_KEY"] = e_key
                self.brain.settings.setdefault("voice_settings", {})["elevenlabs_api_key"] = e_key
        if self.overlay and hasattr(self.overlay, "tts") and self.overlay.tts:
            self.overlay.tts.set_preset(chosen_voice)
        phrase = "A su completo servicio, Amo Víctor. ¿Le agrada cómo suena mi voz anime?"

        import asyncio
        threading.Thread(
            target=lambda: asyncio.run(self.overlay.tts.speak(phrase, mood="happy")),
            daemon=True
        ).start()

    def save_all_settings(self):
        sens_map = {1: 0.90, 2: 0.70, 3: 0.40}
        vad_sens = sens_map.get(self.sens_slider.value(), 0.85)
        mic_gain = self.gain_slider.value() / 10.0
        sil_ms = self.sil_slider.value()
        dev_idx = self.dev_combo.currentData()

        audio_calib = {
            "device_index": dev_idx,
            "mic_gain": mic_gain,
            "vad_sensitivity": vad_sens,
            "silence_timeout_ms": sil_ms
        }

        p = self.brain.personality
        p["name"] = self.name_edit.text().strip() or "Vanessa"
        p["title"] = self.title_edit.text().strip()
        p["system_prompt"] = self.sys_prompt_edit.toPlainText().strip()
        p["speech_style"] = self.style_edit.toPlainText().strip()
        try:
            with open("config/personality.json", "w", encoding="utf-8") as pf:
                json.dump(p, pf, indent=2, ensure_ascii=False)
        except Exception:
            pass
        p["audio_calibration"] = audio_calib

        p["mouse_tracking"] = self.chk_mouse_track.isChecked()
        p["eye_saccades"] = self.chk_saccades.isChecked()
        p["breathing_physics"] = self.chk_breathing.isChecked()
        p["head_patting"] = self.chk_head_pat.isChecked()
        p["music_perception"] = self.chk_music.isChecked()
        p["ambient_voice_only"] = self.chk_ambient_voice.isChecked()

        tts_preset = self.tts_combo.currentData()
        if "voice_settings" not in p:
            p["voice_settings"] = {}
        p["voice_settings"]["online_voice"] = tts_preset
        if hasattr(self, "eleven_key_edit"):
            e_key = self.eleven_key_edit.text().strip()
            self.brain.settings.setdefault("voice_settings", {})["elevenlabs_api_key"] = e_key
            if e_key:
                os.environ["ELEVENLABS_API_KEY"] = e_key
            self.brain.settings["voice_settings"]["voice"] = tts_preset
            try:
                with open(self.brain.settings_path, "w", encoding="utf-8") as f:
                    json.dump(self.brain.settings, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        if self.overlay and hasattr(self.overlay, "tts") and self.overlay.tts:
            self.overlay.tts.set_preset(tts_preset)

        model_data = self.model_combo.currentData()
        mod_type, mod_name = model_data.split(":", 1)
        p["avatar_type"] = mod_type
        if mod_type == "vrm":
            p["vrm_model"] = mod_name
        elif mod_type == "live2d":
            p["live2d_model"] = mod_name
        else:
            p["theme"] = mod_name

        try:
            if hasattr(self.overlay, "memory") and self.overlay.memory:
                self.overlay.memory.save_personality_config(p)
            elif hasattr(self.brain, "memory") and self.brain.memory:
                self.brain.memory.save_personality_config(p)
        except Exception as e:
            print(f"[SettingsDialog] Error guardando en SQLite: {e}")

        self.overlay.mouse_tracking_enabled = p["mouse_tracking"]
        if hasattr(self.overlay, "mouse_track_timer"):
            if p["mouse_tracking"]:
                self.overlay.mouse_track_timer.start(90)
            else:
                self.overlay.mouse_track_timer.stop()

        worker = getattr(self.overlay, "voice_worker", None)
        if worker and hasattr(worker, "listener") and worker.listener:
            worker.listener.update_calibration(
                device_index=dev_idx,
                mic_gain=mic_gain,
                sensitivity=vad_sens,
                silence_ms=sil_ms
            )

        if mod_type == "vrm":
            self.overlay.switch_vrm_model(mod_name)
        elif mod_type == "live2d":
            self.overlay.switch_live2d_model(mod_name)
        else:
            self.overlay.switch_theme(mod_name)

        new_key = self.key_edit.text().strip()
        new_ai_m = self.model_ai_combo.currentData()
        self.brain.set_api_key(new_key)
        self.brain.set_preferred_model(new_ai_m)

        self.overlay.show_balloon("✨ ¡Ajustes y calibración guardados con éxito, Amo Víctor!", duration_ms=4500)
        self.settings_saved_signal.emit()
        self.accept()
