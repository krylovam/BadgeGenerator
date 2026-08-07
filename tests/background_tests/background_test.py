"""Тесты удаления светлого фона с фото и вырезания человека (GrabCut)."""
import numpy as np
from PIL import Image, ImageDraw

from badge_generator.delete_background import (
    remove_background,
    remove_background_grabcut,
)


def _photo_with_light_background() -> Image.Image:
    img = Image.new("RGB", (200, 200), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    # "человек": тёмная фигура в центре, не касающаяся краёв
    draw.rectangle((60, 60, 140, 160), fill=(40, 40, 40))
    draw.ellipse((75, 20, 125, 70), fill=(40, 40, 40))
    return img


def test_remove_background_makes_edges_transparent() -> None:
    rgba = remove_background(_photo_with_light_background())
    assert rgba.mode == "RGBA"
    # углы (фон) — прозрачные
    assert rgba.getpixel((5, 5))[3] == 0
    assert rgba.getpixel((195, 195))[3] == 0
    # фигура осталась непрозрачной
    assert rgba.getpixel((100, 120))[3] == 255


def test_remove_background_keeps_dark_object_inside() -> None:
    rgba = remove_background(_photo_with_light_background())
    # тёмная фигура не пострадала
    assert rgba.getpixel((80, 100))[:3] == (40, 40, 40)
    assert rgba.getpixel((80, 100))[3] == 255


def _portrait_with_face():
    """Фото 300x400: светлый фон, тёмная фигура человека в центре."""
    img = Image.new("RGB", (300, 400), (200, 200, 200))  # нейтральный серый фон
    d = ImageDraw.Draw(img)
    d.rectangle((120, 150, 180, 380), fill=(50, 50, 50))     # тело
    d.ellipse((110, 70, 190, 160), fill=(50, 50, 50))        # голова
    return img


def test_grabcut_cuts_person_from_neutral_background() -> None:
    """GrabCut вырезает человека на нейтральном (не белом) фоне."""
    img = _portrait_with_face()
    face_box = (110, 70, 80, 90)  # примерно голова
    rgba = remove_background_grabcut(img, face_box=face_box)
    assert rgba.mode == "RGBA"
    a = np.asarray(rgba.getchannel("A"))
    # углы (фон) — прозрачны
    assert a[5, 5] == 0 and a[5, -5] == 0
    # центр тела — непрозрачен
    assert a[300, 150] > 200
    # голова — непрозрачна
    assert a[110, 140] > 200


def test_grabcut_without_face_uses_full_frame() -> None:
    """Без рамки лица GrabCut инициализируется всем кадром и не падает."""
    img = _portrait_with_face()
    rgba = remove_background_grabcut(img, face_box=None)
    assert rgba.mode == "RGBA"
    assert rgba.size == img.size


def test_grabcut_keeps_foreground_colors() -> None:
    """Цвета переднего плана сохраняются после вырезания."""
    img = _portrait_with_face()
    rgba = remove_background_grabcut(img, face_box=(110, 70, 80, 90))
    px = rgba.getpixel((150, 300))  # тело
    assert px[3] > 200
    assert px[:3] == (50, 50, 50)
