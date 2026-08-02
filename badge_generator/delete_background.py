"""Удаление фона с фото участника.

Фото снимаются на светлом фоне, поэтому фон удаляется просто: прозрачными
становятся светлые области, соединённые с краем кадра (заливка от границ).
Тёмные предметы и одежда на светлом фоне при этом сохраняются.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def _border_background_mask(near_white: np.ndarray) -> np.ndarray:
    """Маска фона: светлые пиксели, достижимые от краёв кадра (заливка от границ)."""
    h, w = near_white.shape
    source = (near_white.astype(np.uint8)) * 255
    # Маска для floodFill: 1 px рамка вокруг изображения
    ff_mask = np.zeros((h + 2, w + 2), np.uint8)
    for y in range(h):
        for x in (0, w - 1):
            if source[y, x] == 255 and not ff_mask[y + 1, x + 1]:
                cv2.floodFill(source, ff_mask, (x, y), 255, flags=8)
    for x in range(w):
        for y in (0, h - 1):
            if source[y, x] == 255 and not ff_mask[y + 1, x + 1]:
                cv2.floodFill(source, ff_mask, (x, y), 255, flags=8)
    # visited-маска содержит и 1 px рамку — убираем её
    return (ff_mask[1:-1, 1:-1] > 0).astype(np.uint8) * 255


def remove_background(image: Image.Image, threshold: int = 240, feather: int = 3) -> Image.Image:
    """Возвращает RGBA-копию фото с прозрачным светлым фоном.

    :param image: исходное фото (RGB/RGBA).
    :param threshold: яркость, начиная с которой пиксель считается фоном (0-255).
    :param feather: радиус размытия границы прозрачности в пикселях.
    """
    rgb = image.convert("RGB")
    arr = np.asarray(rgb, dtype=np.int16)
    near_white = (arr[:, :, 0] >= threshold) & (arr[:, :, 1] >= threshold) & (arr[:, :, 2] >= threshold)
    bg = _border_background_mask(near_white)

    alpha = 255 - bg  # фон -> прозрачно
    if feather > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=feather)
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)

    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha, mode="L")))
