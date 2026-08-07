"""Шаблон бейджа: загрузка, валидация и сохранение JSON-конфигурации макета.

Конфиг хранится рядом с файлом макета (``<имя_макета>.json``) и описывает
все настраиваемые параметры: размер бейджа, текстовые поля и область фото.
Благодаря этому новый макет подключается без правки кода.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

# Корень проекта (родитель каталога badge_generator)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DPI = 300
DEFAULT_BADGE_SIZE_MM = (100, 70)
DEFAULT_FONT = "assets/Montserrat.ttf"
DEFAULT_FONT_SIZE = 160
DEFAULT_ALIGN = "left"
DEFAULT_COLOR = (0, 0, 0)
DEFAULT_MAX_WIDTH = 0  # 0 = без ограничения
DEFAULT_FACE_SCALE = 0.5
DEFAULT_FACE_OFFSET_Y = 1.1
DEFAULT_NAME_FORMAT = "listener"  # 'listener' = 2 поля, 'staff' = 3 поля (должность)

NAME_FORMATS = ("listener", "staff")

PHOTO_DEFAULTS = {
    "crop_size": [1290, 1470],
    "face_scale": DEFAULT_FACE_SCALE,
    "face_offset_y": DEFAULT_FACE_OFFSET_Y,
    "remove_background": False,
    "border_radius": 0,
}

KNOWN_FIELD_IDS = ("name", "surname")


class TemplateConfigError(Exception):
    """Ошибка в конфигурации шаблона."""


def _as_int_pair(value: Any, name: str, min_value: int = 0) -> Tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise TemplateConfigError(f"Поле '{name}' должно быть списком из двух чисел, получено: {value!r}")
    try:
        result = (int(value[0]), int(value[1]))
    except (TypeError, ValueError):
        raise TemplateConfigError(f"Поле '{name}' должно содержать целые числа, получено: {value!r}")
    if result[0] < min_value or result[1] < min_value:
        raise TemplateConfigError(f"Поле '{name}' не может быть отрицательным: {value!r}")
    return result


def _as_int_quad(value: Any, name: str) -> Tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise TemplateConfigError(f"Поле '{name}' должно быть списком из четырёх чисел [x, y, w, h], получено: {value!r}")
    try:
        result = (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
    except (TypeError, ValueError):
        raise TemplateConfigError(f"Поле '{name}' должно содержать целые числа, получено: {value!r}")
    if min(result) < 0:
        raise TemplateConfigError(f"Поле '{name}' не может содержать отрицательные значения: {value!r}")
    return result


def _as_bool(value: Any, name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise TemplateConfigError(f"Поле '{name}' должно быть true/false, получено: {value!r}")
    return value


def resolve_font_path(font: str, config_dir: Path) -> Path:
    """Ищет файл шрифта: абсолютный путь, путь от каталога конфига или от корня проекта."""
    candidates = []
    p = Path(font)
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.append(config_dir / p)
        candidates.append(PROJECT_ROOT / p)
    for cand in candidates:
        if cand.is_file():
            return cand
    raise TemplateConfigError(
        f"Шрифт не найден: '{font}' (искали в {[str(c) for c in candidates]})"
    )


class TextFieldConfig:
    """Одно текстовое поле на бейдже (имя, фамилия или произвольное)."""

    def __init__(self, data: Dict[str, Any], config_dir: Path):
        self.id: str = str(data.get("id", "")).strip()
        if not self.id:
            raise TemplateConfigError("У текстового поля должен быть непустой 'id'")
        self.label: str = str(data.get("label", self.id))
        self.anchor: Tuple[int, int] = _as_int_pair(data.get("anchor", [0, 0]), f"text_fields['{self.id}'].anchor")
        align = str(data.get("align", DEFAULT_ALIGN)).lower()
        if align not in ("left", "center", "right"):
            raise TemplateConfigError(
                f"text_fields['{self.id}'].align должно быть left/center/right, получено: {align!r}")
        self.align: str = align
        font = str(data.get("font", DEFAULT_FONT))
        self.font: Path = resolve_font_path(font, config_dir)
        try:
            self.font_size: int = int(data.get("font_size", DEFAULT_FONT_SIZE))
        except (TypeError, ValueError):
            raise TemplateConfigError(f"text_fields['{self.id}'].font_size должно быть числом")
        if self.font_size <= 0:
            raise TemplateConfigError(f"text_fields['{self.id}'].font_size должно быть больше нуля")
        color = data.get("color", list(DEFAULT_COLOR))
        if not isinstance(color, (list, tuple)) or not (3 <= len(color) <= 4):
            raise TemplateConfigError(f"text_fields['{self.id}'].color должно быть [r, g, b] или [r, g, b, a]")
        self.color: Tuple[int, int, int, int] = tuple(int(c) for c in color) + (255,) * (4 - len(color))
        try:
            self.max_width: int = int(data.get("max_width", DEFAULT_MAX_WIDTH))
        except (TypeError, ValueError):
            raise TemplateConfigError(f"text_fields['{self.id}'].max_width должно быть числом")
        self.auto_shrink: bool = _as_bool(data.get("auto_shrink", False), f"text_fields['{self.id}'].auto_shrink")
        self.uppercase: bool = _as_bool(data.get("uppercase", False), f"text_fields['{self.id}'].uppercase")
        self.lowercase: bool = _as_bool(data.get("lowercase", False), f"text_fields['{self.id}'].lowercase")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "anchor": list(self.anchor),
            "align": self.align,
            "font": str(self.font.relative_to(PROJECT_ROOT)) if self.font.is_relative_to(PROJECT_ROOT) else str(self.font),
            "font_size": self.font_size,
            "color": list(self.color[:3]),
            "max_width": self.max_width,
            "auto_shrink": self.auto_shrink,
            "uppercase": self.uppercase,
            "lowercase": self.lowercase,
        }


class PhotoConfig:
    """Область фото на бейдже и параметры кадрирования."""

    def __init__(self, data: Optional[Dict[str, Any]]):
        data = data or {}
        self.place_on_badge: Tuple[int, int, int, int] = _as_int_quad(
            data.get("place_on_badge", [0, 0, 1290, 1470]), "photo.place_on_badge")
        self.crop_size: Tuple[int, int] = _as_int_pair(
            data.get("crop_size", PHOTO_DEFAULTS["crop_size"]), "photo.crop_size", min_value=1)
        try:
            self.face_scale: float = float(data.get("face_scale", PHOTO_DEFAULTS["face_scale"]))
            self.face_offset_y: float = float(data.get("face_offset_y", PHOTO_DEFAULTS["face_offset_y"]))
        except (TypeError, ValueError):
            raise TemplateConfigError("photo.face_scale и photo.face_offset_y должны быть числами")
        if self.face_scale <= 0:
            raise TemplateConfigError("photo.face_scale должно быть больше нуля")
        self.remove_background: bool = _as_bool(
            data.get("remove_background", PHOTO_DEFAULTS["remove_background"]), "photo.remove_background")
        try:
            self.border_radius: int = int(data.get("border_radius", 0))
        except (TypeError, ValueError):
            raise TemplateConfigError("photo.border_radius должно быть числом")
        self.border_radius = max(0, self.border_radius)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "place_on_badge": list(self.place_on_badge),
            "crop_size": list(self.crop_size),
            "face_scale": self.face_scale,
            "face_offset_y": self.face_offset_y,
            "remove_background": self.remove_background,
            "border_radius": self.border_radius,
        }


class BadgeTemplate:
    """Конфигурация шаблона бейджа + загруженное изображение макета."""

    def __init__(self, template_file: Path, data: Dict[str, Any]):
        self.template_file: Path = Path(template_file)
        if not self.template_file.is_absolute():
            self.template_file = PROJECT_ROOT / self.template_file
        if not self.template_file.is_file():
            raise TemplateConfigError(f"Файл макета не найден: {self.template_file}")
        self.config_dir: Path = self.template_file.parent

        badge_size_mm = data.get("badge_size_mm", list(DEFAULT_BADGE_SIZE_MM))
        try:
            self.badge_size_mm: Tuple[int, int] = (int(badge_size_mm[0]), int(badge_size_mm[1]))
        except (TypeError, ValueError, IndexError):
            raise TemplateConfigError(f"badge_size_mm должно быть [ширина, высота] в мм, получено: {badge_size_mm!r}")
        if min(self.badge_size_mm) <= 0:
            raise TemplateConfigError("badge_size_mm должно быть положительным")
        try:
            self.dpi: int = int(data.get("dpi", DEFAULT_DPI))
        except (TypeError, ValueError):
            raise TemplateConfigError(f"dpi должно быть числом, получено: {data.get('dpi')!r}")
        if self.dpi <= 0:
            raise TemplateConfigError("dpi должно быть больше нуля")

        fields_data = data.get("text_fields")
        if not isinstance(fields_data, list) or len(fields_data) == 0:
            raise TemplateConfigError("В конфиге должен быть непустой список text_fields")
        self.text_fields: List[TextFieldConfig] = [TextFieldConfig(f, self.config_dir) for f in fields_data]
        ids = [f.id for f in self.text_fields]
        if len(set(ids)) != len(ids):
            raise TemplateConfigError(f"id текстовых полей должны быть уникальны: {ids}")
        # Поле «Должность» (position): выравнивание по центру области,
        # нижний регистр. Якорь — ЛЕВЫЙ край области, max_width — её ширина;
        # текст центрируется внутри этой области. Если max_width=0 — левый
        # край текста остаётся в якоре (ширина не задана, центрирования нет).
        position = self.get_text_field("position")
        if position is not None:
            position.align = "center"
            position.uppercase = False
            position.lowercase = True

        # Имя и фамилия — всегда заглавными буквами (uppercase).
        for fid in ("name", "surname"):
            field = self.get_text_field(fid)
            if field is not None:
                field.uppercase = True
                field.lowercase = False

        name_format = str(data.get("name_format", DEFAULT_NAME_FORMAT)).lower()
        if name_format not in NAME_FORMATS:
            raise TemplateConfigError(
                f"name_format должно быть listener/staff, получено: {name_format!r}")
        self.name_format: str = name_format

        self.photo = PhotoConfig(data.get("photo"))
        self._image: Optional[Image.Image] = None

    # ------------------------------------------------------------------ #
    # Загрузка / сохранение
    # ------------------------------------------------------------------ #
    @classmethod
    def from_json(cls, json_path: Path) -> "BadgeTemplate":
        json_path = Path(json_path)
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise TemplateConfigError(f"Не удалось прочитать конфиг {json_path}: {e}")
        if not isinstance(data, dict):
            raise TemplateConfigError(f"Конфиг {json_path} должен содержать JSON-объект")
        template_file = data.get("template_file")
        if not template_file:
            raise TemplateConfigError(f"В конфиге {json_path} не указан template_file")
        template_path = Path(str(template_file))
        if not template_path.is_absolute():
            template_path = json_path.parent / template_path
        return cls(template_path, data)

    @classmethod
    def from_template_file(cls, template_path: Path, create_default: bool = False) -> "BadgeTemplate":
        """Ищет конфиг <имя макета>.json рядом с макетом."""
        template_path = Path(template_path)
        json_path = template_path.with_suffix(".json")
        if json_path.is_file():
            return cls.from_json(json_path)
        if create_default:
            return cls(template_path, cls.default_config(template_path))
        raise TemplateConfigError(
            f"Рядом с макетом {template_path.name} не найден конфиг {json_path.name}.\n"
            "Нажмите «Настроить шаблон», чтобы создать его."
        )

    @staticmethod
    def default_config(template_path: Path) -> Dict[str, Any]:
        """Разумный конфиг по умолчанию для нового макета (уточняется в мастере)."""
        template_path = Path(template_path)
        try:
            w, h = Image.open(template_path).size
        except OSError:
            w, h = 1181, 827
        photo_w, photo_h = int(w * 0.8), int(h * 0.42)
        return {
            "template_file": template_path.name,
            "badge_size_mm": list(DEFAULT_BADGE_SIZE_MM),
            "dpi": DEFAULT_DPI,
            "name_format": DEFAULT_NAME_FORMAT,
            "text_fields": [
                {
                    "id": "name",
                    "label": "Имя",
                    "anchor": [int(w * 0.12), int(h * 0.52)],
                    "align": "left",
                    "font": DEFAULT_FONT,
                    "font_size": int(h * 0.16),
                    "color": [0, 0, 0],
                    "max_width": int(w * 0.7),
                    "auto_shrink": True,
                    "uppercase": False,
                },
                {
                    "id": "surname",
                    "label": "Фамилия",
                    "anchor": [int(w * 0.12), int(h * 0.72)],
                    "align": "left",
                    "font": DEFAULT_FONT,
                    "font_size": int(h * 0.16),
                    "color": [0, 0, 0],
                    "max_width": int(w * 0.7),
                    "auto_shrink": True,
                    "uppercase": False,
                },
            ],
            "photo": {
                "place_on_badge": [int(w * 0.1), int(h * 0.05), photo_w, photo_h],
                "crop_size": [photo_w, photo_h],
                "face_scale": PHOTO_DEFAULTS["face_scale"],
                "face_offset_y": PHOTO_DEFAULTS["face_offset_y"],
                "remove_background": False,
            },
        }

    def save_json(self, path: Optional[Path] = None) -> Path:
        """Сохраняет конфиг в JSON (по умолчанию рядом с макетом)."""
        if path is None:
            path = self.template_file.with_suffix(".json")
        path = Path(path)
        data = self.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_file": self.template_file.name,
            "badge_size_mm": list(self.badge_size_mm),
            "dpi": self.dpi,
            "name_format": self.name_format,
            "text_fields": [f.to_dict() for f in self.text_fields],
            "photo": self.photo.to_dict(),
        }

    # ------------------------------------------------------------------ #
    # Доступ к данным
    # ------------------------------------------------------------------ #
    @property
    def image(self) -> Image.Image:
        if self._image is None:
            self._image = Image.open(self.template_file).convert("RGB")
        return self._image

    @property
    def size(self) -> Tuple[int, int]:
        return self.image.size

    def get_text_field(self, field_id: str) -> Optional[TextFieldConfig]:
        for f in self.text_fields:
            if f.id == field_id:
                return f
        return None

    def json_path(self) -> Path:
        return self.template_file.with_suffix(".json")
