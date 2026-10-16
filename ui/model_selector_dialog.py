import os
import shutil
from typing import Dict, Any, Callable, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QFileDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer
from PyQt6.QtGui import QFont, QColor

class ModelCard(QFrame):
    def __init__(self, key: str, info: dict, is_active: bool, select_cb: Callable[[str], None], delete_cb: Optional[Callable[[str], None]] = None, parent=None):
        super().__init__(parent)
        self.key = key
        self.select_cb = select_cb
        self.delete_cb = delete_cb
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        border_color = "#38bdf8" if is_active else "#334155"
        bg_color = "#1e293b" if not is_active else "#0f233a"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 12px;
            }}
            QFrame:hover {{
                border-color: #60a5fa;
                background-color: #172554;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header = QHBoxLayout()
        title_lbl = QLabel(info.get("name", key.capitalize()))
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc; border: none; background: transparent;")
        header.addWidget(title_lbl)
        
        if is_active:
            active_badge = QLabel("★ ACTIVO")
            active_badge.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px; background: rgba(56, 189, 248, 0.15); padding: 2px 6px; border-radius: 4px; border: 1px solid #38bdf8;")
            header.addWidget(active_badge)
        header.addStretch()
        layout.addLayout(header)
        
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)
        badges = info.get("badges", [])
        for b in badges:
            badge_lbl = QLabel(b)
            badge_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; background: #0f172a; padding: 2px 6px; border-radius: 4px; border: 1px solid #475569;")
            badges_layout.addWidget(badge_lbl)
        badges_layout.addStretch()
        layout.addLayout(badges_layout)
        
        desc_lbl = QLabel(info.get("desc", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(desc_lbl)
        
        footer = QHBoxLayout()
        size_str = info.get("size", "")
        if size_str:
            size_lbl = QLabel(f"📦 {size_str}")
            size_lbl.setStyleSheet("color: #64748b; font-size: 11px; border: none; background: transparent;")
            footer.addWidget(size_lbl)
        footer.addStretch()
        
        del_btn = QPushButton("🗑️ Eliminar")
        del_btn.setEnabled(not is_active and self.delete_cb is not None)
        if is_active:
            del_btn.setToolTip("No puede eliminar el modelo activo. Cambie a otro modelo primero.")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #475569;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                }
            """)
        else:
            del_btn.setToolTip("Eliminar permanentemente este modelo 3D")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #271418;
                    color: #fca5a5;
                    border: 1px solid #7f1d1d;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #991b1b;
                    color: #ffffff;
                }
            """)
        if self.delete_cb:
            del_btn.clicked.connect(lambda: self.delete_cb(self.key))
        footer.addWidget(del_btn)
        
        btn = QPushButton("Usando actualmente" if is_active else "Activar Modelo")
        btn.setEnabled(not is_active)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {"#0284c7" if not is_active else "#1e293b"};
                color: {"#ffffff" if not is_active else "#64748b"};
                border: 1px solid {"#38bdf8" if not is_active else "#475569"};
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover:enabled {{
                background-color: #0369a1;
            }}
        """)
        btn.clicked.connect(lambda: self.select_cb(self.key))
        footer.addWidget(btn)
        layout.addLayout(footer)


class VanessaModelSelectorDialog(QDialog):
    model_chosen = pyqtSignal(str, str)
    model_deleted = pyqtSignal(str, str)
    
    def __init__(self, models_map: Dict[str, str], current_model: str, parent=None):
        super().__init__(parent)
        self.models_map = dict(models_map)
        self.current_model = current_model
        self.setWindowTitle("Selector de Modelos 3D y Avatares VR / Anime")
        self.setFixedSize(620, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        
        self.model_info = {
            "hoshimachi_suisei": {
                "name": "☄️ Hoshimachi Suisei (Maid Outfit / Hololive)",
                "badges": ["Hololive 0th Gen", "Atuendo Maid de Gala", "Boina Estelar", "Delantal"],
                "desc": "Vocalista estelar de Hololive con su elegante atuendo maid de gala, boina, lazo azul y delantal detallado."
            },
            "houshou_marine": {
                "name": "🏴‍☠️ Houshou Marine (Pirate Captain V2 / Hololive)",
                "badges": ["Hololive 3rd Gen", "Capitana Pirata", "Shaders 4K", "Capa y Sombrero"],
                "desc": "Capitana pirata de Hololive Fantasy con shaders de alta fidelidad 4K, sombrero bicornio y capa ornamentada."
            },
            "inugami_korone": {
                "name": "🥐 Inugami Korone (Bakery Dog / Hololive GAMERS)",
                "badges": ["Hololive GAMERS", "Orejas de Perro", "Pasador Hueso", "Cola Animada"],
                "desc": "Perrita panadera energética de Hololive GAMERS con orejas caninas expresivas, cola suave y pasador de huesito."
            },
            "nekomata_okayu": {
                "name": "🍙 Nekomata Okayu (Chill Cat / Hololive GAMERS)",
                "badges": ["Hololive GAMERS", "Orejas de Gato", "Sudadera Oversized", "Relaxed"],
                "desc": "Gatita relajada de Hololive GAMERS amante de los onigiri. Orejas felinas, sudadera morada y gestos relajados."
            },
            "tsunomaki_watame": {
                "name": "🐑 Tsunomaki Watame (Fluffy Bard / Hololive 4th Gen)",
                "badges": ["Hololive 4th Gen", "Cuernos Espirales", "Capa Afelpada", "Cascabel"],
                "desc": "Ovejita cantante y bardo de Hololive 4th Gen con cuernos en espiral, capa de lana afelpada y cascabel dorado."
            },
            "ouro_kronii": {
                "name": "⏳ Ouro Kronii (Warden of Time / HoloCouncil)",
                "badges": ["Hololive English", "Guardiana del Tiempo", "Diadema Reloj", "Elegante"],
                "desc": "Guardiana del Tiempo de Hololive English -Council- con tocado de reloj, capa asimétrica y presencia imponente."
            },
            "pavolia_reine": {
                "name": "🦚 Pavolia Reine (Peafowl Lady / HoloID 2nd Gen)",
                "badges": ["Hololive ID", "Princesa Pavo Real", "Plumaje Real", "Alta Costura"],
                "desc": "Princesa pavo real de Hololive Indonesia con vestido de alta costura, plumaje estilizado y peinado lateral."
            },
            "hatsune_miku_v4c": {
                "name": "🎵 Hatsune Miku V4C (野餐式 / Picnic Edition)",
                "badges": ["Vocaloid", "Coletas Dobles", "Picnic Edition", "Semi-Standard Bones"],
                "desc": "Hatsune Miku V4 Chinese por Picnic con coletas dobles icónicas, atuendo cibernético, corbata cian y rig MMD con semi-standard bones."
            }
        }
        
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        header_title = QLabel("🎨 Catálogo de Modelos 3D y Avatares")
        header_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_title.setStyleSheet("color: #38bdf8;")
        main_layout.addWidget(header_title)
        
        header_sub = QLabel(
            "Seleccione un modelo anime 3D con soporte para ARKit 52, Visemas OVR y físicas completas, "
            "o cargue cualquier archivo .vrm / .glb desde su equipo (Zenless Zone Zero, Booth, VRChat, etc.)."
        )
        header_sub.setWordWrap(True)
        header_sub.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 4px;")
        main_layout.addWidget(header_sub)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #1e293b;
                border-radius: 8px;
                background-color: #0b0f19;
            }
            QScrollBar:vertical {
                background: #0f172a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
        """)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(8, 8, 8, 8)
        
        self._populate_cards()
        
        scroll.setWidget(self.cards_container)
        main_layout.addWidget(scroll)
        
        actions_layout = QHBoxLayout()
        
        load_custom_btn = QPushButton("📂 Cargar Archivo .vrm / .glb desde mi PC...")
        load_custom_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 9px 16px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        load_custom_btn.clicked.connect(self._browse_custom_model)
        actions_layout.addWidget(load_custom_btn)
        
        open_folder_btn = QPushButton("📁 Abrir Carpeta")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                font-size: 12px;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: white;
            }
        """)
        open_folder_btn.clicked.connect(self._open_vrm_folder)
        actions_layout.addWidget(open_folder_btn)
        
        actions_layout.addStretch()
        
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: white;
                font-size: 12px;
                border-radius: 6px;
                padding: 9px 16px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        main_layout.addLayout(actions_layout)

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

            parent = self.parent()
            if parent and hasattr(parent, "get_current_screen_pos"):
                v_pos = parent.get_current_screen_pos()
                vx = v_pos.x()
                vy = v_pos.y()
                vw = parent.width()
                vh = parent.height()
            elif parent:
                v_pos = parent.pos()
                vx = v_pos.x()
                vy = v_pos.y()
                vw = parent.width()
                vh = parent.height()
            else:
                vx = sw - 420
                vy = sh - 680
                vw = 400
                vh = 650

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
                        ["hyprctl", "dispatch", "movewindowpixel", f"exact {target_x} {target_y},title:^.*Selector de Modelos.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                    subprocess.run(
                        ["hyprctl", "dispatch", "pin", "title:^.*Selector de Modelos.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                    subprocess.run(
                        ["hyprctl", "dispatch", "alterzorder", "top,title:^.*Selector de Modelos.*$"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5
                    )
                except Exception:
                    pass

            QTimer.singleShot(60, _dispatch_hypr)
        except Exception as e:
            print(f"[ModelSelectorDialog] Error adjust_reciprocal_position: {e}")

    def _populate_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        canonical_order = [
            "hoshimachi_suisei", "houshou_marine", "inugami_korone",
            "nekomata_okayu", "tsunomaki_watame", "ouro_kronii",
            "pavolia_reine", "hatsune_miku_v4c"
        ]
        alias_map = {
            "vanessa": "hoshimachi_suisei",
            "suisei": "hoshimachi_suisei",
            "marine": "houshou_marine",
            "korone": "inugami_korone",
            "okayu": "nekomata_okayu",
            "watame": "tsunomaki_watame",
            "kronii": "ouro_kronii",
            "reine": "pavolia_reine",
            "miku": "hatsune_miku_v4c"
        }
        cur_canonical = alias_map.get(self.current_model, self.current_model)
        for key in canonical_order:
            path = self.models_map.get(key)
            if not path:
                continue
            info = self.model_info.get(key, {})
            name = info.get("name", key.capitalize())
            badges = info.get("badges", ["Modelo 3D", "Rig Humanoide"])
            desc = info.get("desc", f"Modelo 3D personalizado cargado desde {os.path.basename(path)}.")
            
            size_str = ""
            if os.path.exists(path):
                sz = os.path.getsize(path) / (1024 * 1024)
                size_str = f"{sz:.1f} MB"
                
            card_info = {
                "name": name,
                "badges": badges,
                "desc": desc,
                "size": size_str
            }
            
            is_active = (key == cur_canonical)
            card = ModelCard(key, card_info, is_active, self._select_model, self._delete_model, self.cards_container)
            self.cards_layout.addWidget(card)
            
        self.cards_layout.addStretch()

    def _delete_model(self, key: str):
        if key == self.current_model:
            QMessageBox.warning(
                self, "Modelo en Uso",
                "No puede eliminar el avatar activo actualmente en Vanessa.\n"
                "Por favor active otro modelo antes de eliminar este."
            )
            return

        path = self.models_map.get(key)
        info = self.model_info.get(key, {})
        name = info.get("name", key.capitalize())

        size_text = ""
        if path and os.path.exists(path):
            sz = os.path.getsize(path) / (1024 * 1024)
            size_text = f" ({sz:.1f} MB)"

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar permanentemente el modelo 3D?\n\n"
            f"• Nombre: {name}\n"
            f"• Archivo: {os.path.basename(path) if path else key}{size_text}\n\n"
            f"El archivo será borrado de su disco para liberar almacenamiento.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                self.models_map.pop(key, None)
                self.model_info.pop(key, None)
                
                if self.parent() and hasattr(self.parent(), "vrm_models_map"):
                    self.parent().vrm_models_map.pop(key, None)
                
                self.model_deleted.emit(key, path or "")
                self._populate_cards()
                
                QMessageBox.information(
                    self, "Modelo Eliminado",
                    f"El modelo '{name}' ha sido eliminado exitosamente del catálogo."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error al Eliminar",
                    f"No se pudo eliminar el archivo del modelo:\n{e}"
                )

    def _select_model(self, key: str):
        if key in self.models_map:
            path = self.models_map[key]
            self.current_model = key
            self.model_chosen.emit(key, path)
            self._populate_cards()

    def _browse_custom_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Modelo 3D (VRM / GLB / GLTF)",
            os.path.expanduser("~"),
            "Archivos 3D (*.vrm *.glb *.gltf);;VRM Models (*.vrm);;GLTF/GLB (*.glb *.gltf);;Todos (*)"
        )
        if file_path and os.path.exists(file_path):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            clean_key = "".join(c for c in base_name if c.isalnum() or c in "_-").lower()
            if not clean_key:
                clean_key = "custom_model"
                
            target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static/vrm_models/custom"))
            os.makedirs(target_dir, exist_ok=True)
            dest_file = os.path.join(target_dir, os.path.basename(file_path))
            try:
                shutil.copy2(file_path, dest_file)
                self.models_map[clean_key] = dest_file
                self.model_info[clean_key] = {
                    "name": f"✨ {base_name} (Personalizado)",
                    "badges": ["Modelo de Usuario", "Rig Humanoide", "Físicas"],
                    "desc": f"Modelo 3D cargado por el usuario desde {file_path}. Compatible con animaciones Mixamo y esqueletos humanoides."
                }
                self.current_model = clean_key
                self.model_chosen.emit(clean_key, dest_file)
                self._populate_cards()
                QMessageBox.information(self, "Modelo Cargado", f"¡El modelo '{base_name}' ha sido cargado con éxito en Vanessa!")
            except Exception as e:
                QMessageBox.warning(self, "Error al Cargar", f"No se pudo copiar el archivo: {e}")

    def _open_vrm_folder(self):
        folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "static/vrm_models"))
        try:
            import subprocess
            subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass
