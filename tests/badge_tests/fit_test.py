"""Тест вписывания фото в область макета без искажения пропорций."""
import json

from PIL import Image

from badge_generator.BadgeGenerator import Badge
from badge_generator.template import BadgeTemplate


def _make_template(tmp_path, photo_place, crop_size):
    png = tmp_path / "t.png"
    Image.new("RGB", (1000, 1000), (255, 255, 255)).save(png)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [100, 100],
        "dpi": 300,
        "text_fields": [{"id": "name", "anchor": [10, 10], "font_size": 50}],
        "photo": {"place_on_badge": photo_place, "crop_size": crop_size},
    }), encoding="utf-8")
    return BadgeTemplate.from_json(cfg)


def _solid_photo(tmp_path) -> str:
    """Однотонное фото: любой кадр из него — красный, детекция лица не нужна."""
    path = tmp_path / "photo.png"
    Image.new("RGB", (800, 800), (200, 30, 30)).save(path)
    return str(path)


def test_photo_fit_preserves_aspect(tmp_path) -> None:
    # область 500x200 (2.5:1), кадр 400x400 (1:1) -> фото 200x200 по центру
    template = _make_template(tmp_path, [100, 100, 500, 200], [400, 400])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # слева от вписанного фото — белое поле (x=100..250), фото — по центру
    assert img.getpixel((120, 200)) == (255, 255, 255)
    # центр области — красное фото
    assert img.getpixel((350, 200)) == (200, 30, 30)


def test_photo_fit_exact_when_aspects_match(tmp_path) -> None:
    # кадр и область одного аспекта -> фото заполняет область целиком
    template = _make_template(tmp_path, [100, 100, 400, 400], [400, 400])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # левый верхний угол области — красное фото, а не белый фон
    assert img.getpixel((110, 110)) == (200, 30, 30)
