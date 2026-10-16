"""
Object Detection & Recognition Database Module for Vanessa.
Uses lightweight NanoDet ONNX model to identify desk/ambient objects
(cups, phones, laptops, books, bottles, etc.) and logs them to SQLite.
"""
import os
import cv2
import time
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional

COCO_CLASSES_ES = [
    "persona", "bicicleta", "coche", "motocicleta", "avión", "autobús", "tren", "camión", "barco",
    "semáforo", "boca de incendios", "señal de stop", "parquímetro", "banco", "pájaro", "gato",
    "perro", "caballo", "oveja", "vaca", "elefante", "oso", "cebra", "jirafa", "mochila",
    "paraguas", "bolso", "corbata", "maleta", "disco volador", "esquís", "snowboard",
    "balón deportivo", "cometa", "bate de béisbol", "guante de béisbol", "monopatín", "tabla de surf",
    "raqueta de tenis", "botella", "copa de vino", "taza de café", "tenedor", "cuchillo", "cuchara",
    "tazón", "plátano", "manzana", "sándwich", "naranja", "brócoli", "zanahoria", "hot dog", "pizza",
    "dona", "pastel", "silla", "sofá", "planta", "cama", "mesa", "inodoro", "pantalla de TV",
    "computadora portátil", "ratón", "control remoto", "teclado", "teléfono celular", "microondas",
    "horno", "tostadora", "fregadero", "refrigerador", "libro", "reloj", "florero", "tijeras",
    "oso de peluche", "secador de pelo", "cepillo de dientes"
]

class ObjectDetector:
    def __init__(
        self,
        model_path: str = "data/object_detection_nanodet_2022nov.onnx",
        db_path: str = "data/assistant_memory.db",
        input_size: int = 416,
        score_thresh: float = 0.40
    ):
        self.model_path = model_path
        self.db_path = db_path
        self.input_size = input_size
        self.score_thresh = score_thresh
        self.net = None
        self._init_db()
        self._load_model()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detected_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    label TEXT,
                    confidence REAL,
                    source TEXT
                )
            ''')
            conn.commit()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.net = cv2.dnn.readNetFromONNX(self.model_path)
            except Exception as e:
                print(f"[ObjectDetector] Error cargando modelo: {e}")

    def detect_objects_in_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Runs inference on a BGR video frame and returns list of detected objects."""
        if self.net is None or frame is None:
            return []

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame,
            1.0 / 255.0,
            (self.input_size, self.input_size),
            (103.53, 116.28, 123.675),
            swapRB=True
        )
        self.net.setInput(blob)
        output = self.net.forward()  # (1, 2704, 80)
        output = output[0]

        detected = []
        seen_classes = set()

        for i in range(output.shape[0]):
            scores = output[i]
            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])

            if confidence >= self.score_thresh:
                label = COCO_CLASSES_ES[class_id] if class_id < len(COCO_CLASSES_ES) else f"objeto_{class_id}"
                if label not in seen_classes:
                    seen_classes.add(label)
                    detected.append({
                        "label": label,
                        "confidence": round(confidence, 2)
                    })

        # Save to database
        if detected:
            self._save_to_database(detected)

        return detected

    def _save_to_database(self, objects: List[Dict[str, Any]]):
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for obj in objects:
                cursor.execute(
                    "INSERT INTO detected_objects (timestamp, label, confidence, source) VALUES (?, ?, ?, ?)",
                    (now, obj["label"], obj["confidence"], "webcam")
                )
            conn.commit()

    def get_recent_detected_objects(self, limit: int = 8) -> List[str]:
        """Returns distinct objects seen in recent minutes."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT label FROM detected_objects WHERE timestamp > ? ORDER BY id DESC LIMIT ?",
                (time.time() - 300, limit)
            )
            rows = cursor.fetchall()
            return [r[0] for r in rows]

    def capture_and_detect_objects(self, camera_index: int = 0) -> List[str]:
        """Opens camera on-demand, detects objects, saves to database, and releases camera immediately."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return []

        # Warm up
        for _ in range(4):
            cap.read()
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return []

        objs = self.detect_objects_in_frame(frame)
        return [o["label"] for o in objs]
