"""
Voice Enrollment Dialog: Bixby-style biometric enrollment with disk dataset (WAV files).
"""
import os
import time
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QGuiApplication
from core.voice_enrollment import VoiceEnrollmentManager
from core.anime_tts import AnimeTTS


class VoiceEnrollmentDialog(QDialog):
    def __init__(self, voice_mgr: VoiceEnrollmentManager, tts: AnimeTTS, voice_worker=None, parent=None):
        super().__init__(parent)
        self.voice_mgr = voice_mgr
        self.tts = tts
        self.voice_worker = voice_worker
        self.setWindowTitle("🎙️ Registro Biométrico de Voz & Dataset Local")
        self.resize(680, 530)
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ec4899, stop:1 #8b5cf6);
                color: white; border-radius: 8px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #db2777; }
            QLineEdit {
                background-color: #1e293b; color: #38bdf8; border: 1px solid #475569;
                border-radius: 6px; padding: 6px 10px; font-family: 'Courier New', monospace; font-size: 12px;
            }
            QProgressBar { border: 1px solid #6366f1; border-radius: 6px; text-align: center; color: white; background: #1e293b; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ec4899, stop:1 #38bdf8); border-radius: 6px; }
            QTableWidget {
                background-color: #1e293b; color: #f8fafc; border: 1px solid #334155;
                border-radius: 8px; gridline-color: #334155;
            }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section {
                background-color: #0f172a; color: #38bdf8; font-weight: bold;
                border: 1px solid #334155; padding: 4px;
            }
        """)

        layout = QVBoxLayout(self)

        # Header Title
        title = QLabel("🎙️ Calibración Biometría & Dataset Local de Voz")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #f472b6;")
        layout.addWidget(title)

        desc = QLabel(
            "Al pulsar <b>'Grabar Muestra'</b>, se capturarán 4 segundos de audio que se guardarán <b>inmediatamente</b>\n"
            "como archivo <b>.wav</b> permanente en tu disco, liberando la memoria RAM y extrayendo armónicos en SQLite.\n\n"
            "Frase de calibración recomendada:\n"
            f"<font color='#38bdf8' size='+1'><b>«{self.voice_mgr.target_phrase}»</b></font>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Dataset Path Container
        path_box = QVBoxLayout()
        path_lbl = QLabel("📁 Ubicación exacta en disco (Dataset permanente):")
        path_lbl.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 12px;")
        path_box.addWidget(path_lbl)

        path_row = QHBoxLayout()
        self.path_field = QLineEdit(self.voice_mgr.dataset_dir)
        self.path_field.setReadOnly(True)
        path_row.addWidget(self.path_field)

        copy_btn = QPushButton("📋 Copiar Ruta")
        copy_btn.setStyleSheet("background: #334155; color: #f8fafc; padding: 6px 12px;")
        copy_btn.clicked.connect(self.copy_dataset_path)
        path_row.addWidget(copy_btn)

        open_btn = QPushButton("📂 Abrir Carpeta")
        open_btn.setStyleSheet("background: #334155; color: #38bdf8; padding: 6px 12px;")
        open_btn.clicked.connect(self.voice_mgr.open_dataset_folder)
        path_row.addWidget(open_btn)

        path_box.addLayout(path_row)
        layout.addLayout(path_box)

        # Status and Progress Bar
        self.status_label = QLabel("Estado: Listo para grabar muestra.")
        self.status_label.setStyleSheet("color: #a5b4fc; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # Table with recordings
        table_lbl = QLabel("Archivos de voz guardados en disco:")
        table_lbl.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 12px; margin-top: 4px;")
        layout.addWidget(table_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Archivo WAV", "Duración", "Tamaño", "Fecha / Acción"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        self.record_btn = QPushButton("🔴 Grabar Muestra de Voz (4 seg)")
        self.record_btn.clicked.connect(self.start_recording)
        btn_box.addWidget(self.record_btn)

        self.train_btn = QPushButton("⚡ Entrenar con Dataset")
        self.train_btn.setStyleSheet("background: #0284c7; color: white;")
        self.train_btn.clicked.connect(self.train_dataset_profile)
        btn_box.addWidget(self.train_btn)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.setStyleSheet("background: #334155; color: #f8fafc;")
        refresh_btn.clicked.connect(self.refresh_table)
        btn_box.addWidget(refresh_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background: #1e293b; border: 1px solid #6366f1;")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)

        layout.addLayout(btn_box)

        # Initial populate
        self.refresh_table()

    def copy_dataset_path(self):
        QGuiApplication.clipboard().setText(self.voice_mgr.dataset_dir)
        self.status_label.setText("📋 ¡Ruta copiada al portapapeles!")
        self.status_label.setStyleSheet("color: #4ade80; font-weight: bold;")

    def refresh_table(self):
        samples = self.voice_mgr.get_dataset_samples()
        self.table.setRowCount(len(samples))
        for row, s in enumerate(samples):
            f_item = QTableWidgetItem(s["filename"])
            f_item.setToolTip(s["path"])
            self.table.setItem(row, 0, f_item)

            d_item = QTableWidgetItem(f"{s.get('duration_sec', 4.0)}s")
            self.table.setItem(row, 1, d_item)

            sz_item = QTableWidgetItem(f"{s.get('size_kb', 0)} KB")
            self.table.setItem(row, 2, sz_item)

            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(4, 2, 4, 2)
            lbl_date = QLabel(s.get("date_str", ""))
            lbl_date.setStyleSheet("font-size: 11px; color: #94a3b8;")
            cell_layout.addWidget(lbl_date)

            play_btn = QPushButton("▶ Oír")
            play_btn.setFixedSize(55, 24)
            play_btn.setStyleSheet("background: #0284c7; color: white; padding: 2px 6px; font-size: 11px; border-radius: 4px;")
            p = s["path"]
            play_btn.clicked.connect(lambda ch, path=p: self.voice_mgr.play_sample(path))
            cell_layout.addWidget(play_btn)

            self.table.setCellWidget(row, 3, cell_widget)

    def start_recording(self):
        self.record_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("🎙️ ¡Grabando ahora! Diga claramente: «Hola Vanessa, soy tu amo Víctor»")
        self.status_label.setStyleSheet("color: #f472b6; font-weight: bold;")

        # Pause wake worker to prevent ALSA/PipeWire mic contention
        if self.voice_worker and hasattr(self.voice_worker, "detector") and self.voice_worker.detector:
            self.voice_worker.detector.pause()

        self.record_start_time = time.time()
        self.record_timer = QTimer(self)
        self.record_timer.timeout.connect(self._update_progress)
        self.record_timer.start(50)

        def _do_record():
            try:
                audio = self.voice_mgr.record_enrollment_sample(duration_sec=4.0)
                success, msg, wav_path, feat = self.voice_mgr.enroll_voice(audio, name="Amo Víctor")
                QTimer.singleShot(0, lambda: self.on_enroll_done(success, msg, wav_path, feat))
            except Exception as e:
                err_msg = str(e)
                QTimer.singleShot(0, lambda: self.on_enroll_done(False, err_msg, "", {}))

        threading.Thread(target=_do_record, daemon=True).start()

    def _update_progress(self):
        elapsed = time.time() - self.record_start_time
        pct = min(100, int((elapsed / 4.0) * 100))
        self.progress.setValue(pct)
        if elapsed >= 4.0:
            self.record_timer.stop()
            self.status_label.setText("💾 Guardando en disco y procesando armónicos...")
            self.status_label.setStyleSheet("color: #38bdf8;")

    def on_enroll_done(self, success: bool, msg: str, wav_path: str, feat: dict):
        if hasattr(self, "record_timer") and self.record_timer.isActive():
            self.record_timer.stop()
        self.progress.setValue(100)
        self.record_btn.setEnabled(True)

        if self.voice_worker and hasattr(self.voice_worker, "detector") and self.voice_worker.detector:
            self.voice_worker.detector.resume()

        if success:
            self.refresh_table()
            fname = os.path.basename(wav_path)
            self.status_label.setText(f"✨ ¡Guardado con éxito!: {fname}")
            self.status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
            QMessageBox.information(
                self, "Grabación Guardada con Éxito",
                f"La muestra se guardó permanentemente en el disco:\n{wav_path}\n\n"
                f"Frecuencia (Pitch): {feat.get('pitch_hz', 125)} Hz\n"
                f"Centroide Espectral: {feat.get('spectral_centroid', 1000)} Hz\n\n"
                "Vanessa ha registrado este archivo en su dataset y lo usará para verificar tu voz."
            )
        else:
            self.status_label.setText(f"❌ Error al grabar: {msg}")
            self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            QMessageBox.warning(self, "Error de Grabación", f"No se pudo guardar la grabación:\n{msg}")

    def train_dataset_profile(self):
        try:
            self.status_label.setText("⚡ Analizando todas las grabaciones del dataset...")
            self.status_label.setStyleSheet("color: #38bdf8; font-weight: bold;")
            QApplication.processEvents()
            profile = self.voice_mgr.train_profile_from_dataset("Amo Víctor")
            if profile and profile.get("sample_count", 0) > 0:
                count = profile.get("sample_count", 0)
                pitch = profile.get("median_pitch", profile.get("mean_pitch", 130))
                floor_hz = profile.get("f0_floor", 85)
                ceiling_hz = profile.get("f0_ceiling", 280)
                centroid = profile.get("spectral_centroid", 1800)
                self.status_label.setText(f"✅ Rango Vocal Calibrado: {floor_hz}Hz - {ceiling_hz}Hz ({count} muestras)")
                self.status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
                QMessageBox.information(
                    self, "Escaneo y Calibración de Rango Vocal",
                    f"¡Perfil Biométrico de Alta Precisión calibrado para el Amo Víctor!\n\n"
                    f"• Grabaciones analizadas: {count} archivos .wav\n"
                    f"• Rango Dinámico Vocal: {floor_hz} Hz a {ceiling_hz} Hz\n"
                    f"• Frecuencia Fundamental Central: {pitch} Hz (Barítono Natural)\n"
                    f"• Huella Espectral Mel: 16 bandas de resonancia acústica del tracto vocal\n\n"
                    "Vanessa ahora filtrará ruidos ajenos y reconocerá exclusivamente tu voz con máxima precisión."
                )
            else:
                self.status_label.setText("⚠️ No se encontraron grabaciones suficientes en el dataset.")
                self.status_label.setStyleSheet("color: #facc15; font-weight: bold;")
        except Exception as e:
            self.status_label.setText(f"❌ Error al calibrar: {e}")
            self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")

    def closeEvent(self, event):
        if hasattr(self, "record_timer") and self.record_timer.isActive():
            self.record_timer.stop()
        if self.voice_worker and hasattr(self.voice_worker, "detector") and self.voice_worker.detector:
            self.voice_worker.detector.resume()
        super().closeEvent(event)
