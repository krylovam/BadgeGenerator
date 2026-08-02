"""Детекция лица на фото (каскад Хаара)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


class FaceDetector:
    def __init__(self, path: str):
        dir_path = Path(__file__).resolve().parent
        self.face_cascade = cv2.CascadeClassifier(str(dir_path / "utils" / "cascade.xml"))
        img_bytes = np.fromfile(path, dtype=np.uint8)
        self.img = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
        if self.img is None:
            raise ValueError(f"Не удалось прочитать изображение: {path}")
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        self.faces: np.ndarray = np.empty((0, 4))

    def detect(self) -> "FaceDetector":
        self.faces = self.face_cascade.detectMultiScale(self.gray, 1.1, 12)
        return self

    def has_faces(self) -> bool:
        return len(self.faces) > 0

    def get_boxes(self) -> Optional[Tuple[int, int, int, int]]:
        """Возвращает (x, y, w, h) первого лица или None, если лиц не найдено."""
        if len(self.faces) == 0:
            return None
        x, y, w, h = self.faces[0]
        return int(x), int(y), int(w), int(h)

    def show_img(self) -> None:
        for (x, y, w, h) in self.faces:
            cv2.rectangle(self.img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.imshow("img", self.img)
        cv2.waitKey()
