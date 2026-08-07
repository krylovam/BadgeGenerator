"""Удаление фона / вырезание человека с фото.

Два способа:
- :func:`remove_background_grabcut` — вырезает человека по силуэту (GrabCut),
  инициализируясь рамкой лица. Работает на ЛЮБОМ фоне (нейтральный, пёстрый,
  тёмный) — лучший выбор для портретов.
- :func:`remove_background` — убирает светлый фон (заливка от границ кадра).
  Подходит только для однотонного светлого фона.
"""
from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

GRABCUT_ITERATIONS = 5
GRABCUT_MAX_WORK_SIZE = 900  # маска считается на уменьшенной копии (быстрее)
GRABCUT_FEATHER = 4          # размытие края маски, px


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


def _person_rect_from_face(face_box: Optional[Tuple[int, int, int, int]],
                           img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    """Прямоугольник вокруг человека по рамке лица (лицо + плечи + корпус)."""
    if face_box is None:
        return (1, 1, img_w - 2, img_h - 2)
    fx, fy, fw, fh = face_box
    x0 = max(0, int(fx - fw * 0.9))
    y0 = max(0, int(fy - fh * 0.6))
    x1 = min(img_w, int(fx + fw * 1.9))
    y1 = min(img_h, int(fy + fh * 4.2))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return (1, 1, img_w - 2, img_h - 2)
    return (x0, y0, x1 - x0, y1 - y0)


def remove_background_grabcut(image: Image.Image,
                              face_box: Optional[Tuple[int, int, int, int]] = None,
                              feather: int = GRABCUT_FEATHER) -> Image.Image:
    """Вырезает человека (передний план) с фото через GrabCut.

    :param image: исходное фото (RGB/RGBA).
    :param face_box: рамка лица (x, y, w, h) — задаёт область человека.
        Если None — GrabCut инициализируется всем кадром.
    :param feather: размытие границы маски в пикселях.
    """
    rgb = image.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    h, w = arr.shape[:2]

    # Считаем маску на уменьшенной копии (быстрее), затем увеличиваем обратно
    scale = min(1.0, GRABCUT_MAX_WORK_SIZE / max(h, w))
    work = cv2.resize(arr, (max(1, round(w * scale)), max(1, round(h * scale))),
                      interpolation=cv2.INTER_AREA) if scale < 1.0 else arr
    wh, ww = work.shape[:2]

    rect = _person_rect_from_face(face_box, w, h)
    rect_s = (max(0, round(rect[0] * scale)), max(0, round(rect[1] * scale)),
              max(1, round(rect[2] * scale)), max(1, round(rect[3] * scale)))

    mask = np.zeros((wh, ww), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(work, mask, rect_s, bgd, fgd, GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_RECT)
        alpha_small = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD),
                               255, 0).astype(np.uint8)
    except cv2.error:
        # GrabCut не смог — запасной вариант: весь кадр непрозрачный
        alpha_small = np.full((wh, ww), 255, np.uint8)

    if scale < 1.0:
        alpha = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        alpha = alpha_small

    if feather > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=feather)
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)

    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha, mode="L")))


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
