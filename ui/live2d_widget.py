"""
Live2D Cubism Native OpenGL Widget for Vanessa Desktop Companion.
Renders Live2D models with 100% transparent alpha blending, physics,
real-time lip-sync, eye tracking, and motion/expression triggering.
"""
import os
import math
import time
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QCursor, QMouseEvent
import live2d
from live2d.utils.canvas import Canvas

# Enable OpenGL RHI backend for Qt6
os.environ["QSG_RHI_BACKEND"] = "opengl"

_LIVE2D_INITIALIZED = False

def ensure_live2d_init():
    global _LIVE2D_INITIALIZED
    if not _LIVE2D_INITIALIZED:
        try:
            live2d.init()
            _LIVE2D_INITIALIZED = True
        except Exception as e:
            print(f"[Live2D] Aviso inicializando live2d: {e}")

# Call init at module load
ensure_live2d_init()


class Live2DWidget(QOpenGLWidget):
    """
    Transparent QOpenGLWidget that renders a Live2D Cubism model
    with natural physics, eye tracking, and speech-driven lip sync.
    """
    clicked_signal = pyqtSignal()
    double_clicked_signal = pyqtSignal()

    def __init__(self, parent=None, model_path: Optional[str] = None):
        super().__init__(parent)
        ensure_live2d_init()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        self.model_path = model_path
        self.model: Optional[live2d.Model] = None
        self.canvas: Optional[Canvas] = None
        self.is_gl_ready = False
        self.model_loaded = False

        # Lip-sync animation state
        self.is_speaking = False
        self.speaking_phase = 0.0

        # Cursor tracking state
        self.track_mouse_enabled = True
        self.drag_x = 0.0
        self.drag_y = 0.0

        # Render & Animation Loop (60 FPS)
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update)
        self.render_timer.start(16)

    def initializeGL(self):
        try:
            ensure_live2d_init()
            live2d.glInit()
            self.canvas = Canvas()
            self.canvas.SetSize(max(10, self.width()), max(10, self.height()))
            self.is_gl_ready = True

            if self.model_path and os.path.exists(self.model_path):
                self._load_model_internal(self.model_path)
            else:
                print(f"[Live2D] Aviso: model_path no encontrado: {self.model_path}")
        except Exception as e:
            print(f"[Live2D] Error en initializeGL: {e}")

    def resizeGL(self, w: int, h: int):
        try:
            if self.canvas:
                self.canvas.SetSize(max(10, w), max(10, h))
            if self.model:
                self.model.Resize(max(10, w), max(10, h))
        except Exception as e:
            print(f"[Live2D] Error en resizeGL: {e}")

    def load_model(self, model_path: str) -> bool:
        """Loads a Live2D model from JSON path or directory."""
        if not os.path.exists(model_path):
            print(f"[Live2D] Ruta no encontrada: {model_path}")
            return False

        if os.path.isdir(model_path):
            # Find .model3.json or .model.json
            found = None
            for root, _, files in os.walk(model_path):
                for f in files:
                    if f.endswith(".model3.json") or f.endswith(".model.json"):
                        found = os.path.join(root, f)
                        break
                if found:
                    break
            if not found:
                print(f"[Live2D] No se encontró .model3.json en {model_path}")
                return False
            model_path = found

        self.model_path = os.path.abspath(model_path)
        if self.is_gl_ready:
            self.makeCurrent()
            success = self._load_model_internal(self.model_path)
            self.doneCurrent()
            return success
        return True

    def _load_model_internal(self, full_json_path: str) -> bool:
        try:
            abs_path = os.path.abspath(full_json_path)
            new_model = live2d.Model()
            new_model.LoadModelJson(abs_path)
            new_model.Resize(max(10, self.width()), max(10, self.height()))
            new_model.SetAutoBreath(True)
            new_model.SetAutoBlink(True)
            self.model = new_model
            self.model_loaded = True
            print(f"[Live2D] Modelo cargado con éxito: {os.path.basename(abs_path)}")
            return True
        except Exception as e:
            print(f"[Live2D] Error cargando modelo {full_json_path}: {e}")
            self.model_loaded = False
            return False

    def _on_draw(self):
        live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)
        if self.model:
            self.model.Draw()

    def paintGL(self):
        if not self.is_gl_ready or not self.model or not self.canvas or not self.model_loaded:
            return

        try:
            # 1. Real-time speech lip sync modulation
            if self.is_speaking:
                self.speaking_phase += 0.38
                # Natural undulating mouth opening
                mouth_open = 0.5 + 0.45 * (math.sin(self.speaking_phase) * math.cos(self.speaking_phase * 0.7))
                mouth_open = max(0.05, min(0.95, mouth_open))
                self.model.SetParamById("ParamMouthOpenY", mouth_open)
            else:
                curr_mouth = self.model.GetParamValueById("ParamMouthOpenY")
                if curr_mouth > 0.02:
                    self.model.SetParamById("ParamMouthOpenY", curr_mouth * 0.72)

            # 2. Eye & Head tracking (smoothly follow global mouse cursor)
            if self.track_mouse_enabled and self.isVisible():
                cursor = QCursor.pos()
                center = self.mapToGlobal(QPoint(self.width() // 2, self.height() // 3))
                dx = float(cursor.x() - center.x())
                dy = float(cursor.y() - center.y())

                # Normalized screen range
                screen = self.screen()
                sw = screen.geometry().width() if screen else 1920
                sh = screen.geometry().height() if screen else 1080

                target_x = max(-1.0, min(1.0, dx / (sw * 0.4)))
                target_y = max(-1.0, min(1.0, dy / (sh * 0.4)))

                self.drag_x += (target_x - self.drag_x) * 0.15
                self.drag_y += (target_y - self.drag_y) * 0.15

                # Live2D Drag maps to eye & head angle
                self.model.Drag(self.drag_x, self.drag_y)

            # 3. Physics & internal animation update
            self.model.Update()

            # 4. Render to canvas and blit with alpha blending
            self.canvas.Draw(self._on_draw)

        except Exception as e:
            pass

    def start_motion(self, group: str = "TapBody", index: Optional[int] = None):
        """Starts a specific motion group or random motion in group."""
        if not self.model or not self.model_loaded:
            return
        try:
            groups = self.model.GetMotionGroups()
            if group in groups:
                if index is not None and index < groups[group]:
                    self.model.StartMotion(group, index, 3)
                else:
                    self.model.StartRandomMotion(group, 3)
            elif "Idle" in groups:
                self.model.StartRandomMotion("Idle", 2)
        except Exception as e:
            print(f"[Live2D] Error iniciando motion {group}: {e}")

    def set_speaking(self, speaking: bool):
        self.is_speaking = speaking
        if speaking:
            self.speaking_phase = 0.0
            # Also trigger an active speaking/reacting motion if available
            self.start_motion("TapBody")

    def set_opacity(self, alpha: float):
        """Sets transparency of the Live2D canvas for sleep mode."""
        if self.canvas:
            self.canvas.SetOutputOpacity(max(0.0, min(1.0, alpha)))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Cute tap reaction
            self.start_motion("TapBody")
            self.clicked_signal.emit()
        event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.double_clicked_signal.emit()
        event.ignore()

    def mouseMoveEvent(self, event: QMouseEvent):
        event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent):
        event.ignore()
