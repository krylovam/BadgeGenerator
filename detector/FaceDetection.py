"""Детекция лица: YuNet (CNN, ONNX) — основная, каскад Хаара — запасная.

YuNet (face_detection_yunet_2023mar.onnx) заметно точнее каскада Хаара:
находит лица в профиль и при плохом освещении, а также возвращает
5 ключевых точек лица (глаза, нос, уголки рта) — по ним фото центрируется
точнее, чем по прямоугольнику.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

MODEL_FILENAME = "face_detection_yunet_2023mar.onnx"
SCORE_THRESHOLD = 0.7
NMS_THRESHOLD = 0.3
TOP_K = 5000


class FaceDetector:
    def __init__(self, path: str, score_threshold: float = SCORE_THRESHOLD):
        dir_path = Path(__file__).resolve().parent
        self._model_path = dir_path / "utils" / MODEL_FILENAME
        self._cascade_path = dir_path / "utils" / "cascade.xml"

        img_bytes = np.fromfile(path, dtype=np.uint8)
        self.img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        if self.img is None:
            raise ValueError(f"Не удалось прочитать изображение: {path}")
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

        self.faces: np.ndarray = np.empty((0, 4))
        self.landmarks: Optional[np.ndarray] = None  # Nx10: 5 точек (x, y) на лицо

        # YuNet
        self._yunet = None
        if self._model_path.is_file():
            try:
                self._yunet = cv2.FaceDetectorYN_create(
                    str(self._model_path), "", (320, 320),
                    score_threshold=score_threshold,
                    nms_threshold=NMS_THRESHOLD,
                    top_k=TOP_K)
            except cv2.error:
                self._yunet = None

        # Запасной каскад Хаара (если модель YuNet недоступна)
        self._cascade = None
        if self._yunet is None and self._cascade_path.is_file():
            self._cascade = cv2.CascadeClassifier(str(self._cascade_path))

        self._engine = "yunet" if self._yunet is not None else "cascade"

    # ------------------------------------------------------------------ #
    def detect(self) -> "FaceDetector":
        if self._yunet is not None:
            h, w = self.img.shape[:2]
            self._yunet.setInputSize((w, h))
            _, faces = self._yunet.detect(self.img)
            if faces is None or len(faces) == 0:
                self.faces = np.empty((0, 4))
                self.landmarks = np.empty((0, 10))
            else:
                self.faces = faces[:, :4]
                self.landmarks = faces[:, 4:14]
        elif self._cascade is not None:
            self.faces = self._cascade.detectMultiScale(self.gray, 1.1, 12)
            self.landmarks = None
        else:
            raise RuntimeError("Нет ни модели YuNet, ни каскада Хаара в detector/utils/")
        return self

    def engine(self) -> str:
        return self._engine

    def has_faces(self) -> bool:
        return len(self.faces) > 0

    def get_boxes(self) -> Optional[Tuple[int, int, int, int]]:
        """Возвращает (x, y, w, h) первого лица или None, если лиц не найдено."""
        if len(self.faces) == 0:
            return None
        x, y, w, h = self.faces[0]
        return int(x), int(y), int(w), int(h)

    def get_landmarks(self) -> Optional[List[Tuple[int, int]]]:
        """5 ключевых точек первого лица: [правый глаз, левый глаз, нос,
        правый угол рта, левый угол рта] — или None."""
        if self.landmarks is None or len(self.landmarks) == 0:
            return None
        pts = self.landmarks[0]
        return [(int(pts[i]), int(pts[i + 1])) for i in range(0, 10, 2)]

    def get_eye_center(self) -> Optional[Tuple[int, int]]:
        """Середина отрезка между глазами (в координатах исходного фото)."""
        landmarks = self.get_landmarks()
        if landmarks is None:
            return None
        x = (landmarks[0][0] + landmarks[1][0]) // 2
        y = (landmarks[0][1] + landmarks[1][1]) // 2
        return x, y

    def show_img(self) -> None:
        img = self.img.copy()
        for (x, y, w, h) in self.faces:
            cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), (255, 0, 0), 2)
        landmarks = self.get_landmarks()
        if landmarks:
            for (lx, ly) in landmarks:
                cv2.circle(img, (lx, ly), 3, (0, 255, 0), -1)
        cv2.imshow("img", img)
        cv2.waitKey()
