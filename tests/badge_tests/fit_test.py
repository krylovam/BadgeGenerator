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
    """Фото заполняет область целиком (cover) без искажения пропорций:
    края фото ровно по границам области, лишнее по краям обрезается."""
    # область 500x200 (2.5:1), кадр 400x400 (1:1) -> фото 500x500,
    # обрезано сверху/снизу до 500x200
    template = _make_template(tmp_path, [100, 100, 500, 200], [400, 400])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # вся область заполнена фото (и у левого края, и в центре)
    assert img.getpixel((120, 200)) == (200, 30, 30)
    assert img.getpixel((350, 200)) == (200, 30, 30)
    # за пределами области — белый макет (фото не выходит за границы)
    assert img.getpixel((90, 200)) == (255, 255, 255)
    assert img.getpixel((350, 90)) == (255, 255, 255)
    assert img.getpixel((350, 310)) == (255, 255, 255)


def test_photo_fit_exact_when_aspects_match(tmp_path) -> None:
    # кадр и область одного аспекта -> фото заполняет область целиком
    template = _make_template(tmp_path, [100, 100, 400, 400], [400, 400])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # левый верхний угол области — красное фото, а не белый фон
    assert img.getpixel((110, 110)) == (200, 30, 30)


def test_photo_right_bottom_edges_exactly_match_area(tmp_path) -> None:
    """Правый и нижний край фото ровно совпадают с границами области
    (не выходят за них) при любых пропорциях кадра и области."""
    # кадр 1290x1470 (портрет), область 400x500 — пропорции разные
    template = _make_template(tmp_path, [100, 100, 400, 500], [1290, 1470])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # пиксели сразу за правой и нижней границей области — белые (макет)
    assert img.getpixel((501, 350)) == (255, 255, 255)
    assert img.getpixel((350, 601)) == (255, 255, 255)
    # пиксели внутри области у правой и нижней границы — фото
    assert img.getpixel((499, 350)) == (200, 30, 30)
    assert img.getpixel((350, 599)) == (200, 30, 30)


def test_small_photo_no_black_padding(tmp_path) -> None:
    """Если фото меньше кадра (crop_size) — не должно быть чёрных полей
    справа/снизу (PIL заполнял выход за границы фото чёрным)."""
    # фото 800x800, кадр 1290x1470 — кадр больше фото
    template = _make_template(tmp_path, [100, 100, 400, 500], [1290, 1470])
    badge = Badge(0, _solid_photo(tmp_path), template)
    img = badge.get_photo()
    # вся область фото — красная (нет чёрных вставок)
    for px, py in [(120, 120), (499, 350), (350, 599), (499, 599)]:
        assert img.getpixel((px, py)) == (200, 30, 30), f"чёрное поле в ({px},{py})"


def test_rounded_corners_photo_area(tmp_path) -> None:
    """Скругление углов области фото (border_radius): фото ОБРЕЗАНО по
    скруглённой маске — в углах виден фон макета (не прозрачные дырки),
    внутри — фото."""
    import json
    tpl = tmp_path / "t.png"
    Image.new("RGB", (1000, 1000), (0, 120, 200)).save(tpl)  # синий фон макета
    photo = tmp_path / "photo.png"
    Image.new("RGB", (800, 800), (200, 30, 30)).save(photo)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [100, 100],
        "dpi": 300,
        "text_fields": [{"id": "name", "anchor": [10, 10], "font_size": 50}],
        "photo": {"place_on_badge": [100, 100, 400, 500], "crop_size": [1290, 1470],
                  "border_radius": 45},
    }), encoding="utf-8")
    template = BadgeTemplate.from_json(cfg)
    badge = Badge(0, str(photo), template)
    img = badge.get_photo()
    # углы области — фон макета (синий), фото обрезано по скруглению
    for px, py in [(100, 100), (499, 100), (100, 599), (499, 599)]:
        assert img.getpixel((px, py))[:3] == (0, 120, 200), f"угол ({px},{py}) не фон"
    # внутри области — фото (красное)
    for px, py in [(150, 150), (300, 350), (498, 350), (300, 599)]:
        assert img.getpixel((px, py))[:3] == (200, 30, 30), f"({px},{py}) не фото"


def test_rounded_corners_zero_radius(tmp_path) -> None:
    """border_radius=0 (по умолчанию) — углы не скругляются."""
    import json
    tpl = tmp_path / "t.png"
    Image.new("RGB", (1000, 1000), (255, 255, 255)).save(tpl)
    photo = tmp_path / "photo.png"
    Image.new("RGB", (800, 800), (200, 30, 30)).save(photo)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [100, 100],
        "dpi": 300,
        "text_fields": [{"id": "name", "anchor": [10, 10], "font_size": 50}],
        "photo": {"place_on_badge": [100, 100, 400, 500], "crop_size": [1290, 1470]},
    }), encoding="utf-8")
    template = BadgeTemplate.from_json(cfg)
    badge = Badge(0, str(photo), template)
    img = badge.get_photo()
    # при radius=0 фото без прозрачности — бейдж RGB
    assert img.mode == "RGB"
    # угол области — фото (не прозрачный)
    assert img.getpixel((100, 100))[:3] == (200, 30, 30)
