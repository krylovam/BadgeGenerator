"""Тесты удаления светлого фона с фото."""
from PIL import Image, ImageDraw

from badge_generator.delete_background import remove_background


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
