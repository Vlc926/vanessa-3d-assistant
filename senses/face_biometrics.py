"""
Facial Biometrics & Recognition Module using SFace (OpenCV 5.0).
Enrolls and verifies the user's face ("Amo Víctor") to distinguish him from strangers.
"""
import os
import json
import sqlite3
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any, List

class FaceBiometrics:
    def __init__(
        self,
        model_path: str = "data/face_recognition_sface_2021dec.onnx",
        db_path: str = "data/assistant_memory.db",
        cosine_threshold: float = 0.363
    ):
        self.model_path = model_path
        self.db_path = db_path
        self.cosine_threshold = cosine_threshold
        self.recognizer = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.recognizer = cv2.FaceRecognizerSF.create(self.model_path, "")
            except Exception as e:
                print(f"[FaceBiometrics] Error cargando SFace: {e}")

    def extract_feature(self, frame: np.ndarray, face_data: np.ndarray) -> Optional[np.ndarray]:
        """Aligns face and extracts 128-d biometric feature vector."""
        if self.recognizer is None or frame is None or face_data is None:
            return None
        try:
            aligned_face = self.recognizer.alignCrop(frame, face_data)
            feature = self.recognizer.feature(aligned_face)
            return feature
        except Exception as e:
            print(f"[FaceBiometrics] Error extrayendo feature: {e}")
            return None

    def enroll_user(self, name: str, frame: np.ndarray, face_data: np.ndarray) -> bool:
        """Stores the face biometric profile in SQLite."""
        feat = self.extract_feature(frame, face_data)
        if feat is None:
            return False

        embedding_list = feat.flatten().tolist()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO face_profiles (name, embedding_json, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(embedding_list), cv2.getTickCount())
            )
            conn.commit()
        return True

    def identify_face(self, frame: np.ndarray, face_data: np.ndarray) -> Tuple[str, float]:
        """Compares current face against database. Returns (name, confidence_score)."""
        feat = self.extract_feature(frame, face_data)
        if feat is None:
            return ("Desconocido", 0.0)

        best_match = "Desconocido"
        best_score = -1.0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, embedding_json FROM face_profiles")
            for row in cursor.fetchall():
                name, emb_json = row[0], row[1]
                try:
                    ref_feat = np.array(json.loads(emb_json), dtype=np.float32).reshape(1, -1)
                    score = self.recognizer.match(feat, ref_feat, cv2.FaceRecognizerSF_FR_COSINE)
                    if score > best_score:
                        best_score = float(score)
                        if score >= self.cosine_threshold:
                            best_match = name
                except Exception:
                    continue

        return (best_match, max(0.0, best_score))

    def capture_and_enroll(
        self,
        camera_index: int = 0,
        name: str = "Amo Víctor",
        yunet_path: str = "data/face_detection_yunet_2023mar.onnx"
    ) -> Tuple[bool, str]:
        """Opens camera, detects primary face with YuNet, and enrolls into SFace database."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return (False, "No se pudo acceder a la cámara frontal.")

        detector = None
        if os.path.exists(yunet_path):
            try:
                detector = cv2.FaceDetectorYN.create(yunet_path, "", (640, 480))
            except Exception as e:
                pass

        if detector is None:
            cap.release()
            return (False, "Detector YuNet no disponible.")

        # Read a few warm-up frames
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return (False, "No se pudo capturar imagen de la cámara.")

        h, w, _ = frame.shape
        detector.setInputSize((w, h))
        _, faces = detector.detect(frame)

        if faces is None or len(faces) == 0:
            return (False, "No se detectó ningún rostro frente a la cámara. Mire de frente con buena iluminación.")

        primary_face = faces[0]
        success = self.enroll_user(name, frame, primary_face)
        if success:
            return (True, f"¡Rostro de '{name}' registrado con éxito en la base biométrica!")
        return (False, "Error al extraer características biométricas del rostro.")
