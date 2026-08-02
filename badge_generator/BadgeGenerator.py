"""Генерация бейджа: текстовые поля и фото по конфигурации шаблона.

Класс :class:`Badge` больше не содержит ни одной константы макета —
все размеры, координаты и шрифты берутся из :class:`BadgeTemplate`
(JSON-конфиг рядом с файлом макета).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from badge_generator.template import BadgeTemplate, TextFieldConfig
from detector.FaceDetection import FaceDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
READY_BADGES_DIR = PROJECT_ROOT / "ready-badges"

MIN_FONT_SIZE = 20
FONT_SHRINK_STEP = 0.9


def parse_name_from_filename(url: str) -> Tuple[str, str]:
    """Разбирает имя и фамилию из имени файла.

    Формат: ``<фамилия>[_<имя>...]``, разделители — пробелы, '_' или '-'.
    Первый токен считается фамилией, остальные — именем.
    Пример: ``кристин_петерсон.jpeg`` -> (surname='Кристин', name='Петерсон').
    """
    base = Path(str(url).replace("\\", "/")).stem
    parts = [p for p in re.split(r"[_\-\s]+", base.strip()) if p]
    if not parts:
        return "", ""
    surname = parts[0].title()
    name = " ".join(parts[1:]).title()
    return surname, name


def _sanitize_filename(value: str) -> str:
    value = value.strip().replace(" ", "_")
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", value)


class Badge:
    """Один бейдж: исходное фото участника + шаблон + текущее положение фото."""

    def __init__(self, id: int, url: str, template: BadgeTemplate):
        self._id = id
        self._url = url
        self._template = template
        self._photo: Optional[Image.Image] = None
        self._photo_x = 0
        self._photo_y = 0
        self._badge_image: Optional[Image.Image] = None
        self._extra: Dict[str, str] = {}
        self._rendered_font_sizes: Dict[str, int] = {}

        self._surname, self._name = parse_name_from_filename(url)
        self.load_photo()
        if template.photo.remove_background:
            # Импорт ленивый: opencv нужен только если функция включена в конфиге
            from badge_generator.delete_background import remove_background
            self._photo = remove_background(self._photo)
        self.detect_face()
        self.render()

    # ------------------------------------------------------------------ #
    # Инициализация
    # ------------------------------------------------------------------ #
    def load_photo(self) -> None:
        self._photo = Image.open(self._url)

    def detect_face(self) -> None:
        """Масштабирует фото по лицу и позиционирует окно кадрирования."""
        cw, ch = self._template.photo.crop_size
        detector = FaceDetector(self._url)
        detector.detect()
        box = detector.get_boxes()
        if box is None:
            # Лицо не найдено — показываем центр кадра
            self._photo_x = max(0, (self._photo.width - cw) // 2)
            self._photo_y = max(0, (self._photo.height - ch) // 2)
            return
        x, y, w, h = box
        scale = self._template.photo.face_scale * cw / w
        new_size = (round(self._photo.width * scale), round(self._photo.height * scale))
        self._photo = self._photo.resize(new_size, Image.Resampling.LANCZOS)
        center_x = (x + w / 2) * scale
        center_y = (y + h / 2) * scale * self._template.photo.face_offset_y
        self._photo_x = int(min(max(0.0, center_x - cw / 2), max(0, self._photo.width - cw)))
        self._photo_y = int(min(max(0.0, center_y - ch / 2), max(0, self._photo.height - ch)))

    # ------------------------------------------------------------------ #
    # Отрисовка
    # ------------------------------------------------------------------ #
    def _text_for(self, field_id: str) -> str:
        if field_id == "name":
            return self._name
        if field_id == "surname":
            return self._surname
        return self._extra.get(field_id, "")

    def _draw_text(self, draw: ImageDraw.ImageDraw, field: TextFieldConfig, text: str) -> None:
        if field.uppercase:
            text = text.upper()
        font_size = field.font_size
        font = ImageFont.truetype(str(field.font), size=font_size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        tw, th = right - left, bottom - top
        if field.max_width and field.auto_shrink and tw > field.max_width:
            while font_size > MIN_FONT_SIZE and tw > field.max_width:
                font_size = max(MIN_FONT_SIZE, int(font_size * FONT_SHRINK_STEP))
                font = ImageFont.truetype(str(field.font), size=font_size)
                left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
                tw, th = right - left, bottom - top
        self._rendered_font_sizes[field.id] = font_size
        x, y = field.anchor
        if field.align == "center":
            x -= tw // 2
        elif field.align == "right":
            x -= tw
        fill = field.color
        if draw._image.mode != "RGBA":  # noqa: SLF001 — Pillow не имеет публичного API
            fill = field.color[:3]
        draw.text((x, y), text, font=font, fill=fill)

    def render(self) -> None:
        """Перерисовывает бейдж целиком (текст + фото) поверх макета."""
        img = self._template.image.copy()
        draw = ImageDraw.Draw(img)
        for field in self._template.text_fields:
            text = self._text_for(field.id)
            if text:
                self._draw_text(draw, field, text)
        if self._photo is not None:
            cw, ch = self._template.photo.crop_size
            cropped = self._photo.crop((self._photo_x, self._photo_y,
                                        self._photo_x + cw, self._photo_y + ch))
            x, y, pw, ph = self._template.photo.place_on_badge
            # вписываем кадр в область без искажения пропорций
            scale = min(pw / cropped.width, ph / cropped.height)
            new_w = max(1, round(cropped.width * scale))
            new_h = max(1, round(cropped.height * scale))
            if (new_w, new_h) != (pw, ph):
                cropped = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
            paste_x = x + (pw - new_w) // 2
            paste_y = y + (ph - new_h) // 2
            if cropped.mode == "RGBA":
                patch = Image.new("RGBA", cropped.size, (255, 255, 255, 255))
                patch = Image.alpha_composite(patch, cropped)
                cropped = patch.convert(img.mode)
            img.paste(cropped, (paste_x, paste_y))
        self._badge_image = img

    # ------------------------------------------------------------------ #
    # Доступ к данным
    # ------------------------------------------------------------------ #
    def get_url(self) -> str:
        return self._url

    def get_name(self) -> str:
        return self._name

    def get_surname(self) -> str:
        return self._surname

    def set_name(self, name: str) -> None:
        self._name = name.strip()
        self.render()

    def set_surname(self, surname: str) -> None:
        self._surname = surname.strip()
        self.render()

    def set_extra(self, field_id: str, value: str) -> None:
        self._extra[field_id] = value.strip()
        self.render()

    def get_photo_coords(self) -> Tuple[int, int]:
        return (self._photo_x, self._photo_y)

    def get_last_font_size(self, field_id: str) -> Optional[int]:
        """Размер шрифта, которым поле реально отрисовано (после auto-shrink)."""
        return self._rendered_font_sizes.get(field_id)

    def get_template(self) -> BadgeTemplate:
        return self._template

    # ------------------------------------------------------------------ #
    # Редактирование положения фото
    # ------------------------------------------------------------------ #
    def translate_photo(self, shift_x: int, shift_y: int) -> None:
        """Сдвигает окно кадрирования (содержимое двигается в противоположную сторону)."""
        cw, ch = self._template.photo.crop_size
        self._photo_x = int(min(max(0, self._photo_x + shift_x), max(0, self._photo.width - cw)))
        self._photo_y = int(min(max(0, self._photo_y + shift_y), max(0, self._photo.height - ch)))
        self.render()

    def scale_photo(self, factor) -> None:
        """Масштабирует фото с сохранением точки в центре окна кадрирования."""
        if isinstance(factor, bool):
            factor = 1.05 if factor else 0.95238095
        cw, ch = self._template.photo.crop_size
        cx = self._photo_x + cw / 2
        cy = self._photo_y + ch / 2
        new_size = (max(1, round(self._photo.width * factor)),
                    max(1, round(self._photo.height * factor)))
        self._photo = self._photo.resize(new_size, Image.Resampling.LANCZOS)
        self._photo_x = int(min(max(0.0, cx * factor - cw / 2), max(0, self._photo.width - cw)))
        self._photo_y = int(min(max(0.0, cy * factor - ch / 2), max(0, self._photo.height - ch)))
        self.render()

    def get_photo_state(self) -> Tuple[int, int, int, int, str, str]:
        """Состояние правок (для undo): координаты, размер фото, имя, фамилия."""
        return (self._photo_x, self._photo_y, self._photo.width, self._photo.height,
                self._name, self._surname)

    def set_photo_state(self, state: Tuple[int, int, int, int, str, str]) -> None:
        self._photo_x, self._photo_y, pw, ph, self._name, self._surname = state
        self._photo = self._photo.resize((pw, ph), Image.Resampling.LANCZOS)
        self.render()

    # ------------------------------------------------------------------ #
    # Вывод
    # ------------------------------------------------------------------ #
    def get_preview_image(self, max_size: Tuple[int, int] = (720, 540)) -> Image.Image:
        """Превью бейджа (PIL Image) для показа в интерфейсе."""
        image = self._badge_image.convert("RGBA")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image

    def get_photo(self) -> Image.Image:
        return self._badge_image

    def save_badge(self, output_dir: Optional[Path] = None) -> Path:
        """Сохраняет бейдж в PNG. Возвращает путь к файлу."""
        output_dir = Path(output_dir) if output_dir else READY_BADGES_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{_sanitize_filename(self._surname)}_{_sanitize_filename(self._name)}_badge.png"
        path = output_dir / filename
        self._badge_image.save(path)
        return path
