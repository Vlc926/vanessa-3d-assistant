"""
Vision, Face Biometrics & Object Recognition Sense.
Combines:
- YuNet for 5-point landmark face tracking
- SFace for Biometric Face Identification ("Amo Víctor")
- NanoDet for Object Detection (cups, phones, laptops, books) stored in DB
"""
import os
import cv2
import time
import threading
import numpy as np
from typing import Dict, Any, Optional, Callable, List
from senses.face_biometrics import FaceBiometrics
from core.object_detector import ObjectDetector

class VisionObserver:
    def __init__(
        self,
        camera_index: int = 0,
        sample_interval: float = 3.5,
        model_path: str = "data/face_detection_yunet_2023mar.onnx",
        width: int = 640,
        height: int = 480
    ):
        self.camera_index = camera_index
        self.sample_interval = sample_interval
        self.model_path = model_path
        self.width = width
        self.height = height

        # Load Biometrics & Object Detector
        self.biometrics = FaceBiometrics()
        self.object_detector = ObjectDetector()

        # Load YuNet detector
        self.detector = None
        if os.path.exists(self.model_path):
            try:
                self.detector = cv2.FaceDetectorYN.create(
                    self.model_path,
                    "",
                    (self.width, self.height),
                    score_threshold=0.6,
                    nms_threshold=0.3
                )
            except Exception as e:
                print(f"[Vision] Error al inicializar YuNet: {e}")

        self.is_running = False
        self.enabled = True
        self.thread: Optional[threading.Thread] = None

        # Last captured frame & face for enrollment
        self.last_frame: Optional[np.ndarray] = None
        self.last_primary_face: Optional[np.ndarray] = None

        # State cache
        self.current_state = {
            "camera_active": False,
            "user_present": False,
            "recognized_user": "Ninguno",
            "confidence": 0.0,
            "face_count": 0,
            "smiling": False,
            "detected_objects": [],
            "last_seen_timestamp": 0.0,
            "presence_duration_seconds": 0.0,
            "description": "Cámara inicializando."
        }

        self.on_state_change_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._observation_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self.current_state["camera_active"] = False
            self.current_state["description"] = "Cámara desactivada por privacidad."

    def enroll_current_user(self, name: str = "Amo Víctor") -> bool:
        """Enrolls the currently detected face as the Master."""
        if self.last_frame is not None and self.last_primary_face is not None:
            return self.biometrics.enroll_user(name, self.last_frame, self.last_primary_face)
        return False

    def _observation_loop(self):
        cap = None
        user_first_seen = None

        while self.is_running:
            if not self.enabled:
                if cap and cap.isOpened():
                    cap.release()
                    cap = None
                time.sleep(1.0)
                continue

            try:
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(self.camera_index)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(1.0)
                    continue

                self.last_frame = frame.copy()
                h, w, _ = frame.shape
                if self.detector is not None:
                    self.detector.setInputSize((w, h))
                    _, faces = self.detector.detect(frame)
                else:
                    faces = None

                now = time.time()
                face_count = len(faces) if faces is not None else 0
                is_smiling = False
                recognized_name = "Desconocido"
                conf = 0.0

                if face_count > 0:
                    self.current_state["user_present"] = True
                    self.current_state["face_count"] = face_count
                    self.current_state["last_seen_timestamp"] = now

                    if user_first_seen is None:
                        user_first_seen = now
                    presence_sec = now - user_first_seen
                    self.current_state["presence_duration_seconds"] = presence_sec

                    # Analyze primary face
                    primary_face = faces[0]
                    self.last_primary_face = primary_face

                    # 1. Face Biometric Identification
                    recognized_name, conf = self.biometrics.identify_face(frame, primary_face)
                    self.current_state["recognized_user"] = recognized_name
                    self.current_state["confidence"] = round(conf, 2)

                    # 2. Smile calculation
                    if len(primary_face) >= 14:
                        mouth_width = abs(primary_face[12] - primary_face[10])
                        face_width = primary_face[2]
                        if face_width > 0 and (mouth_width / face_width) > 0.42:
                            is_smiling = True

                    self.current_state["smiling"] = is_smiling

                    desc = f"{recognized_name} frente a la pantalla ({int(presence_sec)}s)."
                    if is_smiling:
                        desc += " Con una sonrisa."
                    if face_count > 1:
                        desc += f" Detectadas {face_count} personas en la toma."
                    self.current_state["description"] = desc
                else:
                    user_first_seen = None
                    self.current_state["user_present"] = False
                    self.current_state["recognized_user"] = "Ninguno"
                    self.current_state["face_count"] = 0
                    self.current_state["smiling"] = False
                    self.current_state["presence_duration_seconds"] = 0.0
                    self.current_state["description"] = "No se detecta a nadie frente a la cámara."

                # 3. Object Recognition in environment
                objs = self.object_detector.detect_objects_in_frame(frame)
                self.current_state["detected_objects"] = [o["label"] for o in objs]

                self.current_state["camera_active"] = True

                if self.on_state_change_callback:
                    try:
                        self.on_state_change_callback(self.current_state)
                    except Exception:
                        pass

            except Exception as e:
                self.current_state["description"] = f"Visión en espera: {e}"

            time.sleep(self.sample_interval)

        if cap and cap.isOpened():
            cap.release()

    def get_summary(self) -> str:
        s = self.current_state
        objs_str = ", ".join(s["detected_objects"]) if s.get("detected_objects") else "ninguno relevante"
        return f"{s.get('description', '')} Objetos en el entorno: {objs_str}."
