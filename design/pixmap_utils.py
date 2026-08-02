"""Вспомогательные функции конвертации PIL <-> Qt."""
from __future__ import annotations

from typing import Tuple

from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    """Конвертирует PIL-изображение в QPixmap (без PIL.ImageQt)."""
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage)


def load_pixmap(path: str, max_size: Tuple[int, int]) -> QPixmap:
    """Загружает изображение из файла и уменьшает до max_size (сохраняя пропорции)."""
    image = Image.open(path).convert("RGB")
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return pil_to_pixmap(image)
