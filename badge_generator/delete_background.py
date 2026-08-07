"""Удаление фона / вырезание человека с фото.

Способы:
- :func:`remove_background_rembg` — библиотека rembg (U²-Net через
  onnxruntime) с локальной моделью ``u2netp.onnx``. Рекомендуемый способ —
  именно он использовался в оригинальном приложении.
- :func:`remove_background_unet` — та же модель U²-Net, но через OpenCV DNN
  (запасной вариант, если rembg/onnxruntime не установлены).
- :func:`remove_background_grabcut` — GrabCut по рамке лица (может обрезать руки).
- :func:`remove_background` — убирает светлый фон по яркости (только для
  однотонного светлого фона).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

GRABCUT_ITERATIONS = 5
GRABCUT_MAX_WORK_SIZE = 900  # маска считается на уменьшенной копии (быстрее)
GRABCUT_FEATHER = 4          # размытие края маски, px

MODELS_DIR = Path(__file__).resolve().parent / "models"
U2NET_MODEL = MODELS_DIR / "u2netp.onnx"
U2NET_SIZE = 320            # входной размер сети
U2NET_FEATHER = 3           # размытие края маски, px
U2NET_THRESHOLD = 0.5       # порог бинаризации маски

# rembg-сессия создаётся один раз и переиспользуется (иначе каждое фото
# заново грузило бы модель — медленно)
_rembg_session = None
_rembg_model_used = None


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


def _to_rgba(rgb: Image.Image, alpha: np.ndarray) -> Image.Image:
    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha, mode="L")))


def remove_background_rembg(image: Image.Image, model_path: Path = U2NET_MODEL) -> Image.Image:
    """Вырезает человека с фото библиотекой rembg (как в оригинальном приложении).

    Модель загружается из локального файла (не качается из интернета).
    Сессия создаётся один раз и переиспользуется.

    :param image: исходное фото (RGB/RGBA).
    :param model_path: путь к ONNX-модели (u2netp.onnx по умолчанию).
    :raises ImportError: если rembg/onnxruntime не установлены.
    :raises FileNotFoundError: если файл модели не найден.
    """
    global _rembg_session, _rembg_model_used
    try:
        from rembg import new_session, remove
    except ImportError as e:
        raise ImportError(
            "Библиотека rembg не установлена. Установите: pip install 'rembg[cpu]'"
        ) from e

    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Модель U²-Net не найдена: {model_path}\n"
            "Положите u2netp.onnx в папку badge_generator/models/")

    # rembg скачивает модель через pooch в папку U2NET_HOME.
    # Указываем нашу локальную папку с моделью — pooch найдёт файл
    # и не будет качать из интернета.
    os.environ["U2NET_HOME"] = str(MODELS_DIR)

    if _rembg_session is None or _rembg_model_used != str(model_path):
        _rembg_session = new_session("u2netp")
        _rembg_model_used = str(model_path)
    return remove(image, session=_rembg_session)


def remove_background_unet(image: Image.Image, model_path: Path = U2NET_MODEL,
                           threshold: float = U2NET_THRESHOLD,
                           feather: int = U2NET_FEATHER) -> Image.Image:
    """Вырезает человека с фото нейросетью U²-Net (как rembg).

    :param image: исходное фото (RGB/RGBA).
    :param model_path: путь к ONNX-модели (u2netp.onnx по умолчанию).
    :param threshold: порог отнесения пикселя к человеку (0..1).
    :param feather: размытие границы маски в пикселях.
    :raises FileNotFoundError: если файл модели не найден.
    """
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Модель U²-Net не найдена: {model_path}\n"
            "Положите u2netp.onnx в папку badge_generator/models/")
    rgb = image.convert("RGB")
    arr = np.asarray(rgb, dtype=np.uint8)
    h, w = arr.shape[:2]

    net = cv2.dnn.readNetFromONNX(str(model_path))
    blob = cv2.dnn.blobFromImage(arr, 1 / 255.0, (U2NET_SIZE, U2NET_SIZE),
                                 (0.485, 0.456, 0.406), swapRB=True, crop=False)
    blob = blob / np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
    net.setInput(blob)
    out = net.forward()[0, 0]  # (320, 320)

    mask = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    alpha = np.where(mask >= threshold, 255, 0).astype(np.uint8)
    if feather > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), sigmaX=feather)
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    return _to_rgba(rgb, alpha)


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

    return _to_rgba(rgb, alpha)


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

    return _to_rgba(rgb, alpha)
