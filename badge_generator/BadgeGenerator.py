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


def parse_name_from_filename(url: str, mode: str = "listener") -> Tuple[str, str, str]:
    """Разбирает имя, фамилию (и должность) из имени файла.

    Формат: ``<фамилия> <имя> [<должность>] ...``, разделители — пробелы, '_' или '-'.

    - mode='listener' (слушатель): берутся первые 2 токена — фамилия и имя,
      всё остальное (отчество, класс, номер и т.п.) игнорируется.
      Пример: ``Петров Пётр Петрович 1 11.jpg`` -> ('Пётр', 'Петров', '').
    - mode='staff' (педсостав): берутся первые 3 токена — фамилия, имя,
      должность. Пример: ``Иванов Иван Вожатый.png`` -> ('Иван', 'Иванов',
      'Вожатый').

    Хвостовые токены из одних цифр отбрасываются.
    """
    base = Path(str(url).replace("\\", "/")).stem
    parts = [p for p in re.split(r"[_\-\s]+", base.strip()) if p]
    while parts and parts[-1].isdigit():
        parts.pop()
    surname = parts[0].title() if parts else ""
    name = parts[1].title() if len(parts) > 1 else ""
    position = parts[2].title() if mode == "staff" and len(parts) > 2 else ""
    return surname, name, position


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
        self._photo_original: Optional[Image.Image] = None
        self._photo_scale: float = 1.0  # текущий масштаб относительно оригинала
        self._photo_x = 0
        self._photo_y = 0
        self._badge_image: Optional[Image.Image] = None
        self._extra: Dict[str, str] = {}
        self._position: str = ""
        self._rendered_font_sizes: Dict[str, int] = {}
        self._face_box: Optional[Tuple[int, int, int, int]] = None
        self._eye_center: Optional[Tuple[int, int]] = None

        self._surname, self._name, self._position = parse_name_from_filename(
            url, mode=template.name_format)
        self.load_photo()
        # Сначала детектируем лицо (нужно для GrabCut и кадрирования)
        self._detect_face_only()
        if template.photo.remove_background:
            self._remove_background()
        # Оригинал (после удаления фона) — от него всегда пересчитывается зум,
        # чтобы многократные нажатия не деградировали качество.
        self._photo_original = self._photo.copy()
        self.apply_face_crop()
        self.render()

    def _remove_background(self) -> None:
        """Вырезает человека с фото библиотекой rembg."""
        from badge_generator.delete_background import remove_background_rembg
        self._photo = remove_background_rembg(self._photo)

    # ------------------------------------------------------------------ #
    # Инициализация
    # ------------------------------------------------------------------ #
    def load_photo(self) -> None:
        self._photo = Image.open(self._url)

    def detect_face(self) -> None:
        """Находит лицо на фото (YuNet) и применяет кадрирование по лицу."""
        self._detect_face_only()
        self.apply_face_crop()

    def _detect_face_only(self) -> None:
        """Только детекция лица (без кадрирования) — хранит рамку и глаза."""
        detector = FaceDetector(self._url)
        detector.detect()
        self._face_box = detector.get_boxes()
        self._eye_center = detector.get_eye_center()

    def apply_face_crop(self, keep_position: bool = False) -> None:
        """Масштабирует фото по лицу и позиционирует окно кадрирования.

        Вызывается повторно, если в конфиге изменились параметры photo
        (crop_size, face_scale, face_offset_y) или при зуме.
        Горизонтально фото центрируется по середине отрезка между глазами
        (YuNet даёт ключевые точки лица), вертикально — по прямоугольнику
        лица с учётом face_offset_y из конфига.

        :param keep_position: если True — координаты окна не пересчитываются
            (используются текущие _photo_x/_photo_y).
        """
        cw, ch = self._template.photo.crop_size
        box = self._face_box
        # базовый масштаб: чтобы лицо (шириной w) заняло face_scale от ширины
        # кадра; зум пользователя (_photo_scale) умножается сверху.
        if box is None:
            # Лицо не найдено — центрируем кадр, но зум ВСЁ РАВНО применяем
            # (иначе кнопки +/− «не реагируют» на таких фото).
            total_scale = self._photo_scale
            new_size = (max(1, round(self._photo_original.width * total_scale)),
                        max(1, round(self._photo_original.height * total_scale)))
            self._photo = self._photo_original.resize(new_size, Image.Resampling.LANCZOS)
            self._photo_x = max(0, (self._photo.width - cw) // 2)
            self._photo_y = max(0, (self._photo.height - ch) // 2)
            return
        x, y, w, h = box
        face_scale = self._template.photo.face_scale * cw / w
        total_scale = face_scale * self._photo_scale
        new_size = (max(1, round(self._photo_original.width * total_scale)),
                    max(1, round(self._photo_original.height * total_scale)))
        self._photo = self._photo_original.resize(new_size, Image.Resampling.LANCZOS)
        # координаты центра лица в масштабе оригинала
        if self._eye_center is not None:
            center_x = self._eye_center[0] * total_scale
        else:
            center_x = (x + w / 2) * total_scale
        center_y = (y + h / 2) * total_scale * self._template.photo.face_offset_y
        if not keep_position:
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
        if field_id == "position":
            return self._position
        return self._extra.get(field_id, "")

    def _draw_text(self, draw: ImageDraw.ImageDraw, field: TextFieldConfig, text: str) -> None:
        if field.uppercase:
            text = text.upper()
        elif field.lowercase:
            text = text.lower()
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
            # Центрирование по ОБЛАСТИ: якорь — ЛЕВЫЙ край области шириной
            # max_width, текст выравнивается по центру этой области.
            # Если ширина не задана (0) — левый край текста остаётся в якоре
            # (никакого сдвига вокруг точки).
            if field.max_width:
                x += (field.max_width - tw) // 2
        elif field.align == "right":
            x -= tw
        fill = field.color
        if draw._image.mode != "RGBA":  # noqa: SLF001 — Pillow не имеет публичного API
            fill = field.color[:3]
        draw.text((x, y), text, font=font, fill=fill)

    def render(self) -> None:
        """Перерисовывает бейдж целиком (текст + фото) поверх макета."""
        img = self._template.image.copy()
        # работаем в RGBA, если фото с прозрачностью (удалён фон) или
        # область фото со скруглёнными углами — прозрачность нужна до конца
        need_alpha = (self._photo is not None and self._photo.mode == "RGBA") or \
                     self._template.photo.border_radius > 0
        if need_alpha:
            img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        for field in self._template.text_fields:
            text = self._text_for(field.id)
            if text:
                self._draw_text(draw, field, text)
        if self._photo is not None:
            cw, ch = self._template.photo.crop_size
            # Кадр не должен выходить за границы фото: PIL при выходе за край
            # заполняет область чёрным — это давало «чёрные поля» справа/снизу.
            crop_right = min(self._photo.width, self._photo_x + cw)
            crop_bottom = min(self._photo.height, self._photo_y + ch)
            if crop_right <= self._photo_x or crop_bottom <= self._photo_y:
                # фото меньше кадра — берём всё фото
                cropped = self._photo
            else:
                cropped = self._photo.crop((self._photo_x, self._photo_y,
                                            crop_right, crop_bottom))
            x, y, pw, ph = self._template.photo.place_on_badge
            # Заполняем область фото целиком (cover): масштабируем так, чтобы
            # фото покрывало всю область, затем обрезаем ровно по её границам.
            # Края фото ВСЕГДА совпадают с границами области — ни одна сторона
            # не выходит за них и не оставляет полей.
            scale = max(pw / cropped.width, ph / cropped.height)
            new_w = max(1, round(cropped.width * scale))
            new_h = max(1, round(cropped.height * scale))
            if (new_w, new_h) != (cropped.width, cropped.height):
                cropped = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
            paste_x = x + (pw - new_w) // 2
            paste_y = y + (ph - new_h) // 2
            # Обрезка по границам области фото (cover: часть фото за краями).
            left_crop = max(0, x - paste_x)
            top_crop = max(0, y - paste_y)
            right_crop = max(0, (paste_x + new_w) - (x + pw))
            bottom_crop = max(0, (paste_y + new_h) - (y + ph))
            if left_crop or top_crop or right_crop or bottom_crop:
                cropped = cropped.crop((left_crop, top_crop,
                                        new_w - right_crop, new_h - bottom_crop))
                new_w, new_h = cropped.size
                paste_x += left_crop
                paste_y += top_crop
            # Страховка: не даём фото рисоваться за пределами макета.
            # Если область в конфиге выходит за край — обрезаем кадр по краю.
            if paste_x < 0:
                cropped = cropped.crop((-paste_x, 0, new_w, new_h))
                new_w = cropped.width
                paste_x = 0
            if paste_y < 0:
                cropped = cropped.crop((0, -paste_y, new_w, new_h))
                new_h = cropped.height
                paste_y = 0
            over_w = paste_x + new_w - img.width
            over_h = paste_y + new_h - img.height
            if over_w > 0:
                cropped = cropped.crop((0, 0, max(1, new_w - over_w), new_h))
                new_w = cropped.width
            if over_h > 0:
                cropped = cropped.crop((0, 0, new_w, max(1, new_h - over_h)))
                new_h = cropped.height
            # Скругление углов области фото (border_radius из конфига):
            # ОБРЕЗАЕМ само фото по закруглённой маске (вместо наложения
            # маски на итоговое изображение). Так углы фото отсутствуют,
            # и под ними виден фон макета — без «дырок»/прозрачных углов.
            radius = self._template.photo.border_radius
            if radius > 0 and cropped.width > 0 and cropped.height > 0:
                cropped = self._crop_rounded(cropped, radius)
            if cropped.mode == "RGBA":
                # вклеиваем с сохранением прозрачности (на случай удаления фона)
                if img.mode == "RGBA":
                    region = img.crop((paste_x, paste_y,
                                       paste_x + cropped.width,
                                       paste_y + cropped.height)).convert("RGBA")
                    blended = Image.alpha_composite(region, cropped)
                    img.paste(blended, (paste_x, paste_y))
                else:
                    patch = Image.new("RGBA", cropped.size, (255, 255, 255, 255))
                    patch = Image.alpha_composite(patch, cropped)
                    img.paste(patch.convert(img.mode), (paste_x, paste_y))
            else:
                img.paste(cropped, (paste_x, paste_y))
        self._badge_image = img

    @staticmethod
    def _crop_rounded(image: Image.Image, radius: int) -> Image.Image:
        """Обрезает image по закруглённой маске: углы становятся прозрачными.

        Возвращает RGBA-изображение, где пиксели за пределами скруглённого
        прямоугольника прозрачны (при вставке под ними виден фон макета).
        """
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        w, h = image.size
        radius = max(1, min(radius, w // 2, h // 2))
        # маска: 255 внутри скруглённого прямоугольника, 0 в углах
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((radius, 0, w - radius - 1, h - 1), fill=255)   # центр по X
        draw.rectangle((0, radius, w - 1, h - radius - 1), fill=255)   # центр по Y
        draw.rectangle((radius, radius, w - radius - 1, h - radius - 1), fill=255)
        # углы — четверти круга
        corners = ((radius, radius, -1, -1),
                   (w - radius - 1, radius, 1, -1),
                   (radius, h - radius - 1, -1, 1),
                   (w - radius - 1, h - radius - 1, 1, 1))
        for cx, cy, sx, sy in corners:
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        draw.point((cx + sx * dx, cy + sy * dy), fill=255)
        # прозрачность = исходная альфа (если была) * маска скругления
        alpha = image.getchannel("A")
        new_alpha = Image.composite(alpha, Image.new("L", (w, h), 0), mask)
        image.putalpha(new_alpha)
        return image

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
        if field_id == "position":
            self.set_position(value)
            return
        self._extra[field_id] = value.strip()
        self.render()

    def get_position(self) -> str:
        return self._position

    def set_position(self, position: str) -> None:
        self._position = position.strip()
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
        """Масштабирует фото с сохранением точки в центре окна кадрирования.

        Зум всегда пересчитывается от ОРИГИНАЛА (_photo_original), а не от
        текущего уменьшенного кадра — многократные нажатия не накапливают
        потери качества.
        """
        if isinstance(factor, bool):
            factor = 1.05 if factor else 0.95238095
        self._photo_scale = max(0.05, min(20.0, self._photo_scale * factor))
        self.apply_face_crop()
        self.render()  # обновляем бейдж после изменения масштаба

    def get_photo_state(self) -> Tuple[int, int, int, int, str, str, str]:
        """Состояние правок (для undo): координаты, размер фото, имя, фамилия, должность."""
        return (self._photo_x, self._photo_y, self._photo.width, self._photo.height,
                self._name, self._surname, self._position)

    def set_photo_state(self, state: Tuple[int, int, int, int, str, str, str]) -> None:
        (self._photo_x, self._photo_y, pw, ph,
         self._name, self._surname, self._position) = state
        # восстанавливаем масштаб из размера фото относительно оригинала
        if self._photo_original is not None and self._photo_original.width > 0:
            self._photo_scale = pw / self._photo_original.width
        # координаты уже восстановлены из state — не пересчитываем по лицу
        self.apply_face_crop(keep_position=True)
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
