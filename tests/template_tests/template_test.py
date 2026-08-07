"""Тесты конфигурации шаблона (JSON) и разбора имён из имени файла."""
import json
import os

import pytest
from PIL import Image

from badge_generator.BadgeGenerator import parse_name_from_filename
from badge_generator.template import (
    BadgeTemplate,
    TextFieldConfig,
    TemplateConfigError,
    resolve_font_path,
)

dir_path = os.path.dirname(__file__)
TEMPLATE_PATH = f"{dir_path}/../assets/1отряд.png"


def test_template_loaded_from_sibling_json() -> None:
    template = BadgeTemplate.from_template_file(TEMPLATE_PATH)
    assert template.badge_size_mm == (100, 70)
    assert template.dpi == 300
    assert template.size == (1181, 827)
    assert template.get_text_field("name") is not None
    assert template.get_text_field("surname") is not None
    assert template.photo.place_on_badge == (285, 1102, 1290, 1470)
    assert template.photo.crop_size == (1290, 1470)


def test_config_missing_raises() -> None:
    with pytest.raises(TemplateConfigError):
        BadgeTemplate.from_template_file("/nonexistent/template.png")


def test_invalid_config_rejected(tmp_path) -> None:
    png = tmp_path / "t.png"
    png.write_bytes(b"not an image")
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({"template_file": "t.png", "text_fields": []}), encoding="utf-8")
    with pytest.raises(TemplateConfigError):
        BadgeTemplate.from_json(cfg)


def test_duplicate_field_ids_rejected(tmp_path) -> None:
    png = tmp_path / "t.png"
    png.write_bytes(b"not an image")
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "text_fields": [
            {"id": "name", "anchor": [1, 1], "font_size": 10},
            {"id": "name", "anchor": [2, 2], "font_size": 10},
        ],
    }), encoding="utf-8")
    with pytest.raises(TemplateConfigError):
        BadgeTemplate.from_json(cfg)


def test_save_load_roundtrip(tmp_path) -> None:
    import shutil
    shutil.copy(TEMPLATE_PATH, tmp_path / "1отряд.png")
    shutil.copy(f"{dir_path}/../assets/1отряд.json", tmp_path / "1отряд.json")
    template = BadgeTemplate.from_template_file(tmp_path / "1отряд.png")
    saved = template.save_json(tmp_path / "custom.json")
    loaded = BadgeTemplate.from_json(saved)
    assert loaded.to_dict() == template.to_dict()
    assert loaded.badge_size_mm == template.badge_size_mm
    assert len(loaded.text_fields) == len(template.text_fields)


def test_default_config_creatable(tmp_path) -> None:
    # копируем реальный макет, чтобы default_config смог узнать его размер
    import shutil
    dst = tmp_path / "1отряд.png"
    shutil.copy(TEMPLATE_PATH, dst)
    template = BadgeTemplate.from_template_file(dst, create_default=True)
    assert len(template.text_fields) == 2
    assert template.get_text_field("name") is not None
    assert template.get_text_field("surname") is not None
    # сохраняется рядом с макетом
    path = template.save_json()
    assert path == dst.with_suffix(".json")
    assert path.is_file()


def test_font_resolution() -> None:
    resolved = resolve_font_path("assets/Montserrat.ttf", config_dir=dir_path)
    assert resolved.is_file()


@pytest.mark.parametrize("filename,expected", [
    # слушатель: 2 поля (имя, фамилия), остальное игнорируется
    ("кристин_петерсон.jpeg", ("Кристин", "Петерсон", "")),
    ("ivanov petr.jpg", ("Ivanov", "Petr", "")),
    ("смирнова-анна.png", ("Смирнова", "Анна", "")),
    ("безразделителя.jpg", ("Безразделителя", "", "")),
    ("пустой.jpg", ("Пустой", "", "")),
    ("фролова_арина_2_10.jpg", ("Фролова", "Арина", "")),
    ("Фролова Арина Сергеевна 2 10.jpg", ("Фролова", "Арина", "")),
    ("Петров Пётр Петрович 1 11.jpg", ("Петров", "Пётр", "")),
])
def test_parse_name_from_filename_listener(filename: str, expected: tuple) -> None:
    assert parse_name_from_filename(filename, mode="listener") == expected


@pytest.mark.parametrize("filename,expected", [
    # педсостав: 3 поля (имя, фамилия, должность)
    ("Иванов Иван Вожатый.png", ("Иванов", "Иван", "Вожатый")),
    ("Смирнова Ольга Методист 3 12.png", ("Смирнова", "Ольга", "Методист")),
    ("Петров Пётр.jpg", ("Петров", "Пётр", "")),
])
def test_parse_name_from_filename_staff(filename: str, expected: tuple) -> None:
    assert parse_name_from_filename(filename, mode="staff") == expected


def test_name_format_in_template_roundtrip(tmp_path) -> None:
    """name_format сохраняется в JSON и читается обратно."""
    import shutil
    shutil.copy(TEMPLATE_PATH, tmp_path / "1отряд.png")
    shutil.copy(f"{dir_path}/../assets/1отряд.json", tmp_path / "1отряд.json")
    template = BadgeTemplate.from_template_file(tmp_path / "1отряд.png")
    assert template.name_format == "listener"
    template.name_format = "staff"
    saved = template.save_json(tmp_path / "custom.json")
    loaded = BadgeTemplate.from_json(saved)
    assert loaded.name_format == "staff"


def test_staff_position_field_roundtrip(tmp_path) -> None:
    """Поле «Должность», добавленное как в главном меню (в память),
    должно сохраняться в JSON и читаться обратно (align=center, lowercase)."""
    import shutil
    shutil.copy(TEMPLATE_PATH, tmp_path / "1отряд.png")
    shutil.copy(f"{dir_path}/../assets/1отряд.json", tmp_path / "1отряд.json")
    template = BadgeTemplate.from_template_file(tmp_path / "1отряд.png")
    template.name_format = "staff"

    # то же, что делает main_menu._add_position_field
    surname = template.get_text_field("surname")
    anchor = (surname.anchor[0], surname.anchor[1] + int(surname.font_size * 1.5))
    template.text_fields.append(TextFieldConfig({
        "id": "position",
        "label": "Должность",
        "anchor": anchor,
        "align": "center",
        "font": "assets/Montserrat.ttf",
        "font_size": max(40, int(surname.font_size * 0.65)),
        "max_width": surname.max_width,
        "auto_shrink": True,
        "uppercase": False,
        "lowercase": True,
    }, template.config_dir))

    assert template.get_text_field("position") is not None
    saved = template.save_json(tmp_path / "custom.json")
    loaded = BadgeTemplate.from_json(saved)
    assert loaded.name_format == "staff"
    pos = loaded.get_text_field("position")
    assert pos is not None
    assert pos.label == "Должность"
    assert pos.align == "center"
    assert pos.lowercase is True


def test_loading_config_preserves_photo_settings(tmp_path) -> None:
    """Загрузка сохранённого конфига не должна менять положение фото,
    кадр и масштаб (регрессия: setValue спиннеров пересчитывал их)."""
    import json
    import shutil
    shutil.copy(TEMPLATE_PATH, tmp_path / "1отряд.png")

    cfg = tmp_path / "1отряд.json"
    cfg.write_text(json.dumps({
        "template_file": "1отряд.png",
        "badge_size_mm": [100, 70],
        "dpi": 300,
        "name_format": "listener",
        "text_fields": [
            {"id": "name", "anchor": [100, 100], "font_size": 80},
            {"id": "surname", "anchor": [100, 250], "font_size": 80},
        ],
        "photo": {
            "place_on_badge": [123, 45, 400, 500],
            "crop_size": [640, 800],
            "face_scale": 0.42,
            "face_offset_y": 1.15,
            "remove_background": True,
            # старые ключи, которых больше нет — должны игнорироваться
            "remove_bg_threshold": 195,
            "remove_bg_mode": "brightness",
        },
    }), encoding="utf-8")

    template = BadgeTemplate.from_template_file(tmp_path / "1отряд.png")
    assert template.photo.place_on_badge == (123, 45, 400, 500)
    assert template.photo.crop_size == (640, 800)
    assert template.photo.face_scale == 0.42
    assert template.photo.face_offset_y == 1.15
    assert template.photo.remove_background is True
    # повторная загрузка (имитация повторного открытия мастера) — то же самое
    template2 = BadgeTemplate.from_json(cfg)
    assert template2.photo.place_on_badge == (123, 45, 400, 500)
    assert template2.photo.crop_size == (640, 800)
    assert template2.photo.face_scale == 0.42


def test_old_config_position_normalized_on_load(tmp_path) -> None:
    """Старый конфиг с position align=left при загрузке нормализуется:
    align=center, lowercase=True, якорь сдвинут вправо (текст не уезжает)."""
    import json
    import shutil
    shutil.copy(TEMPLATE_PATH, tmp_path / "1отряд.png")
    cfg = tmp_path / "1отряд.json"
    cfg.write_text(json.dumps({
        "template_file": "1отряд.png",
        "badge_size_mm": [100, 70],
        "dpi": 300,
        "name_format": "staff",
        "text_fields": [
            {"id": "name", "anchor": [100, 100], "font_size": 80},
            {"id": "surname", "anchor": [100, 250], "font_size": 80},
            {"id": "position", "label": "Должность", "anchor": [100, 400],
             "align": "left", "font": "assets/Montserrat.ttf", "font_size": 60,
             "max_width": 700, "auto_shrink": True, "uppercase": False},
        ],
        "photo": {"place_on_badge": [100, 600, 400, 200], "crop_size": [400, 200]},
    }), encoding="utf-8")
    template = BadgeTemplate.from_template_file(tmp_path / "1отряд.png")
    pos = template.get_text_field("position")
    assert pos is not None
    assert pos.align == "center"
    assert pos.lowercase is True
    assert pos.uppercase is False
    # якорь сдвинут вправо на ~font_size*2, y не изменился
    assert pos.anchor[0] == 100 + 60 * 2
    assert pos.anchor[1] == 400


def test_remove_background_flag_roundtrip(tmp_path) -> None:
    """Флаг remove_background сохраняется в JSON, старые ключи игнорируются."""
    import json
    tpl = tmp_path / "t.png"
    Image.new("RGB", (500, 500), (255, 255, 255)).save(tpl)
    cfg = tmp_path / "t.json"
    cfg.write_text(json.dumps({
        "template_file": "t.png",
        "badge_size_mm": [50, 50],
        "dpi": 300,
        "text_fields": [{"id": "name", "anchor": [10, 10], "font_size": 30}],
        "photo": {"place_on_badge": [10, 100, 200, 200], "crop_size": [200, 200],
                  "remove_background": True, "remove_bg_mode": "brightness"},
    }), encoding="utf-8")
    template = BadgeTemplate.from_json(cfg)
    assert template.photo.remove_background is True
    saved = template.save_json(tmp_path / "out.json")
    loaded = BadgeTemplate.from_json(saved)
    assert loaded.photo.remove_background is True
    assert "remove_bg_mode" not in json.loads(saved.read_text(encoding="utf-8"))["photo"]
