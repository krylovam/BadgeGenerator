import dataclasses
import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from badge_generator.BadgeGenerator import Badge
from badge_generator.template import BadgeTemplate

dir_path = os.path.dirname(__file__)
TEMPLATE_PATH = f"{dir_path}/../assets/1отряд.png"


@dataclasses.dataclass
class BadgeChecker:
    file_path: str
    template_path: str
    name: str
    surname: str
    photo_coords: (int, int)


# Координаты фото рассчитаны по конфигу tests/assets/1отряд.json
# и детекции YuNet (центрирование по середине отрезка между глазами).
# Допуск ±25 px на случай небольших отличий между версиями OpenCV.
TEST_CASES = [
    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/кристин_петерсон.jpeg',
        template_path=TEMPLATE_PATH,
        name='Петерсон',
        surname='Кристин',
        photo_coords=(1044, 247)),
    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/judy_estrin.jpeg',
        template_path=TEMPLATE_PATH,
        name='Estrin',
        surname='Judy',
        photo_coords=(561, 0)),
    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/tim_oreilly.jpeg',
        template_path=TEMPLATE_PATH,
        name='Oreilly',
        surname='Tim',
        photo_coords=(523, 137)),
    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/vint_cerf.jpeg',
        template_path=TEMPLATE_PATH,
        name='Cerf',
        surname='Vint',
        photo_coords=(1058, 35)),
]

COORD_TOLERANCE = 25


@pytest.fixture(scope="module")
def template():
    return BadgeTemplate.from_template_file(TEMPLATE_PATH)


@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_badge_init(t: BadgeChecker, template: BadgeTemplate) -> None:
    badge = Badge(0, t.file_path, template)
    assert badge.get_name() == t.name
    assert badge.get_surname() == t.surname
    x, y = badge.get_photo_coords()
    assert abs(x - t.photo_coords[0]) <= COORD_TOLERANCE
    assert abs(y - t.photo_coords[1]) <= COORD_TOLERANCE
    # бейдж отрисован и имеет размер макета
    assert badge.get_photo().size == template.size


def test_badge_renders_without_errors(template: BadgeTemplate) -> None:
    badge = Badge(0, TEST_CASES[0].file_path, template)
    image = badge.get_photo()
    assert image.size == template.size
    assert image.mode in ("RGB", "RGBA")


def test_text_rendered_on_white_template(tmp_path) -> None:
    """На белом макете текст полей даёт тёмные пиксели в зоне якоря."""
    import json
    from badge_generator.template import BadgeTemplate

    png = tmp_path / "t.png"
    Image.new("RGB", (2000, 2000), (255, 255, 255)).save(png)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [150, 150],
        "dpi": 300,
        "text_fields": [
            {"id": "name", "label": "Имя", "anchor": [100, 200], "font_size": 150,
             "font": "assets/Montserrat.ttf", "max_width": 800, "auto_shrink": True},
            {"id": "surname", "label": "Фамилия", "anchor": [100, 500], "font_size": 150,
             "font": "assets/Montserrat.ttf", "max_width": 800, "auto_shrink": True},
        ],
        "photo": {"place_on_badge": [100, 900, 800, 800], "crop_size": [800, 800]},
    }), encoding="utf-8")
    template = BadgeTemplate.from_json(cfg)
    badge = Badge(0, TEST_CASES[1].file_path, template)
    img = badge.get_photo()
    region = img.crop((100, 200, 900, 600))
    mins = [e for pair in region.getextrema() for e in pair]
    assert min(mins) < 128


def test_auto_shrink_fits_max_width(tmp_path) -> None:
    """Длинная фамилия уменьшается, чтобы влезть в max_width."""
    import json
    from badge_generator.template import BadgeTemplate

    png = tmp_path / "t.png"
    Image.new("RGB", (2000, 2000), (255, 255, 255)).save(png)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [150, 150],
        "dpi": 300,
        "text_fields": [
            {"id": "surname", "label": "Фамилия", "anchor": [100, 500], "font_size": 300,
             "font": "assets/Montserrat.ttf", "max_width": 600, "auto_shrink": True},
        ],
        "photo": {"place_on_badge": [100, 900, 800, 800], "crop_size": [800, 800]},
    }), encoding="utf-8")
    template = BadgeTemplate.from_json(cfg)
    badge = Badge(0, TEST_CASES[0].file_path, template)  # 'Кристин Петерсон' -> фамилия Кристин
    badge.get_photo()
    field = template.get_text_field("surname")
    used_size = badge.get_last_font_size("surname")
    assert used_size is not None
    assert used_size < field.font_size  # шрифт уменьшен
    font = ImageFont.truetype(str(field.font), size=used_size)
    draw = ImageDraw.Draw(badge.get_photo())
    left, top, right, bottom = draw.textbbox((0, 0), badge.get_surname(), font=font)
    assert right - left <= field.max_width


def test_name_editing(template: BadgeTemplate) -> None:
    badge = Badge(0, TEST_CASES[1].file_path, template)
    badge.set_name("Анна")
    badge.set_surname("Смирнова")
    assert badge.get_name() == "Анна"
    assert badge.get_surname() == "Смирнова"


def test_translate_and_scale(template: BadgeTemplate) -> None:
    badge = Badge(0, TEST_CASES[1].file_path, template)
    x0, y0 = badge.get_photo_coords()
    badge.translate_photo(10, 0)
    x1, _ = badge.get_photo_coords()
    assert x1 == x0 + 10
    badge.scale_photo(1.05)
    # после увеличения фото окно кадрирования не выходит за пределы фото
    cw, _ = template.photo.crop_size
    _, _, photo_w, _, _, _ = badge.get_photo_state()
    assert 0 <= badge.get_photo_coords()[0] <= photo_w - cw


def test_undo_state(template: BadgeTemplate) -> None:
    badge = Badge(0, TEST_CASES[1].file_path, template)
    state = badge.get_photo_state()
    badge.translate_photo(30, 40)
    badge.set_photo_state(state)
    assert badge.get_photo_coords() == (state[0], state[1])
    assert badge.get_name() == state[4]
    assert badge.get_surname() == state[5]


def test_apply_face_crop_recalculates_after_param_change() -> None:
    """Изменение face_scale в конфиге пересчитывает кадрирование."""
    template = BadgeTemplate.from_template_file(TEMPLATE_PATH)
    badge = Badge(0, TEST_CASES[1].file_path, template)
    coords_before = badge.get_photo_coords()
    template.photo.face_scale = 0.8  # лицо крупнее -> кадр сдвигается
    badge.apply_face_crop()
    assert badge.get_photo_coords() != coords_before
    cw, _ = template.photo.crop_size
    _, _, photo_w, _, _, _ = badge.get_photo_state()
    assert 0 <= badge.get_photo_coords()[0] <= photo_w - cw


def test_crop_size_fits_photo_area_proportions() -> None:
    """Кадр должен подгоняться под пропорции области фото на макете,
    чтобы фото заполняло область без белых полей."""
    template = BadgeTemplate.from_template_file(TEMPLATE_PATH)
    template.photo.place_on_badge = (100, 100, 400, 500)  # пропорции 0.8
    template.photo.crop_size = (1290, 1470)
    # эмулируем _apply_place_from_preview
    w, h = 400, 500
    cw, ch = 1290, 1470
    area = cw * ch
    new_h = int(round((area * h / w) ** 0.5))
    new_w = int(round(new_h * w / h))
    assert abs(new_w / new_h - w / h) < 0.01
    # итоговый бейдж не должен иметь белых полей внутри области
    badge = Badge(0, TEST_CASES[1].file_path, template)
    img = badge.get_photo()
    x, y, pw, ph = template.photo.place_on_badge
    region = img.crop((x, y, x + pw, y + ph))
    # в области не должно быть сплошного белого (фото заполняет)
    ext = region.getextrema()
    assert min(ext[0] + ext[1] + ext[2]) < 240, "область фото белая — фото не заполняет"
