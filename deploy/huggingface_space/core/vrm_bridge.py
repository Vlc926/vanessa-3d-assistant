from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer
import math
import time

class VRMBridge(QObject):
    avatar_ready = pyqtSignal()
    avatar_clicked = pyqtSignal(str, float, float)  # part ('head', 'torso', 'legs'), x, y
    gesture_event = pyqtSignal(str, str)  # gesture_name, event ('press', ...)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = None
        self.is_talking = False
        self.talk_timer = QTimer(self)
        self.talk_timer.timeout.connect(self._update_talking)
        self.talk_timer.setInterval(50)  # 20 fps for lip sync
        self.start_time = time.time()

    def set_page(self, page):
        self.page = page

    @pyqtSlot(str, float, float)
    def on_avatar_clicked(self, part: str, x: float, y: float):
        self.avatar_clicked.emit(part, x, y)

    @pyqtSlot(str, str)
    def on_gesture_event(self, gesture: str, event: str):
        self.gesture_event.emit(gesture, event)

    @pyqtSlot()
    def on_avatar_ready(self):
        print("VRM Avatar loaded in JS.")
        self.avatar_ready.emit()

    @pyqtSlot(str, float)
    def set_expression(self, name, weight):
        if self.page:
            self.page.runJavaScript(f"window.vrmController && window.vrmController.setExpression('{name}', {weight});")

    @pyqtSlot(float)
    def set_mouth_open(self, ratio):
        if self.page:
            self.page.runJavaScript(f"window.vrmController && (window.vrmController.updateVisemeLipSync ? window.vrmController.updateVisemeLipSync({ratio}) : window.vrmController.setMouth({ratio}));")

    @pyqtSlot(str, float)
    def set_morph_target(self, name, weight):
        if self.page:
            self.page.runJavaScript(f"window.vrmController && window.vrmController.setMorphTarget('{name}', {weight});")

    @pyqtSlot(str)
    def set_emotion(self, mood):
        self.set_expression("neutral", 0.0)
        self.set_expression(mood, 1.0)

    @pyqtSlot()
    def start_talking(self):
        self.is_talking = True
        self.start_time = time.time()
        self.talk_timer.start()

    @pyqtSlot()
    def stop_talking(self):
        self.is_talking = False
        self.talk_timer.stop()
        if self.page:
            self.page.runJavaScript("window.vrmController && (window.vrmController.resetLipSync ? window.vrmController.resetLipSync() : window.vrmController.setMouth(0.0));")

    def _update_talking(self):
        if not self.is_talking:
            return
            
        # Simple procedural lip sync oscillation
        t = time.time() - self.start_time
        # Combine a couple of sine waves for a somewhat natural "talking" oscillation
        mouth_val = (math.sin(t * 15.0) + math.sin(t * 22.0)) * 0.5
        mouth_val = max(0.0, min(1.0, mouth_val + 0.3)) # Shift and clamp
        
        self.set_mouth_open(mouth_val)
