#!/usr/bin/env python3
"""Автоматическое создание конфига шаблона по паре «макет + готовый бейдж».

Сравнивает макет (пустой) и готовый бейдж (с уже вставленными именем, фамилией
и фото) и определяет, где на макете находятся текстовые поля и область фото.
Это избавляет от ручной расстановки в мастере при переносе старого шаблона.

Использование:
    python tools/derive_config.py <макет.png> <готовый_бейдж.png> [--out config.json]

Требования:
    — готовый бейдж — это тот же макет, но с добавленными текстом и фото
      (например, результат старой версии приложения);
    — имя/фамилия на готовом бейдже читаются из имени файла
      (первый токен — фамилия, остальные — имя).

После генерации откройте конфиг в мастере настройки шаблона, чтобы поправить
детали (порядок полей, размер шрифта, размер бейджа в мм).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from badge_generator.template import (  # noqa: E402
    DEFAULT_FACE_OFFSET_Y,
    DEFAULT_FACE_SCALE,
    DEFAULT_FONT,
    PROJECT_ROOT,
)

DIFF_THRESHOLD = 25       # порог разницы пикселей «макет vs готовый бейдж»
MIN_CHANGE_AREA = 0.0003  # минимальная площадь изменённой области (доля от кадра)
PHOTO_MIN_AREA = 0.05     # фото — самая большая изменённая область (доля от кадра)
LINE_OVERLAP = 0.4        # доля вертикального перекрытия для объединения в строку


def load_rgb(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.asarray(img, dtype=np.int16)


def diff_mask(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if a.shape != b.shape:
        h, w = b.shape[:2]
        a = cv2.resize(np.clip(a, 0, 255).astype(np.uint8), (w, h),
                       interpolation=cv2.INTER_AREA).astype(np.int16)
    diff = np.max(np.abs(a - b), axis=2)
    return (diff > DIFF_THRESHOLD).astype(np.uint8) * 255


def changed_boxes(mask: np.ndarray, img_w: int, img_h: int):
    """Связанные компоненты изменений -> список (x, y, w, h) в пикселях макета."""
    kernel = np.ones((9, 9), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    total = img_w * img_h
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < MIN_CHANGE_AREA * total:
            continue
        boxes.append((int(x), int(y), int(w), int(h), int(area)))
    boxes.sort(key=lambda b: -b[4])  # по убыванию площади
    return merge_into_lines(boxes)


def merge_into_lines(boxes):
    """Объединяет фрагменты одной строки текста (буквы, разделённые пробелами)
    в общий прямоугольник строки по вертикальному перекрытию."""
    lines = []
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        bx, by, bw, bh, area = b
        placed = False
        for line in lines:
            ly0, ly1 = line[1], line[1] + line[3]
            overlap = min(by + bh, ly1) - max(by, ly0)
            if overlap > LINE_OVERLAP * min(bh, line[3]):
                nx0 = min(line[0], bx)
                ny0 = min(line[1], by)
                nx1 = max(line[0] + line[2], bx + bw)
                ny1 = max(line[1] + line[3], by + bh)
                line[0], line[1], line[2], line[3] = nx0, ny0, nx1 - nx0, ny1 - ny0
                line[4] += area
                placed = True
                break
        if not placed:
            lines.append([bx, by, bw, bh, area])
    return [tuple(l) for l in lines]


def text_anchor_from_box(box, text: str, font_path: Path, font_size: int):
    """Возвращает якорь текста: PIL рисует текст с отступом внутри em-бокса,
    поэтому координата верхнего левого угла пикселей не равна anchor."""
    from PIL import ImageDraw, ImageFont
    probe = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(probe)
    font = ImageFont.truetype(str(font_path), size=font_size)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    bx, by, bw, bh = box[:4]
    return [bx - left, by - top]


def generate_config(template_path: Path, ready_path: Path) -> dict:
    """Строит конфиг шаблона по паре «макет + готовый бейдж».

    Возвращает dict-конфиг (как в JSON). При проблемах кидает ValueError
    с понятным сообщением.
    """
    template_path = Path(template_path)
    ready_path = Path(ready_path)
    if not template_path.is_file() or not ready_path.is_file():
        raise ValueError("Файлы не найдены.")

    tpl = load_rgb(template_path)
    ready = load_rgb(ready_path)
    img_h, img_w = ready.shape[:2]
    mask = diff_mask(tpl, ready)
    boxes = changed_boxes(mask, img_w, img_h)

    if not boxes:
        raise ValueError("Не найдено изменений между макетом и готовым бейджем — "
                         "убедитесь, что это один и тот же макет.")

    # Самая большая область — фото, остальные — текст
    photo_box = boxes[0] if boxes[0][4] >= PHOTO_MIN_AREA * img_w * img_h else None
    text_boxes = [b for b in boxes if b is not photo_box]
    text_boxes.sort(key=lambda b: (b[1], b[0]))  # сверху вниз, слева направо

    # Имя/фамилия из имени файла готового бейджа
    from badge_generator.BadgeGenerator import parse_name_from_filename
    surname, name = parse_name_from_filename(str(ready_path))

    font_path = PROJECT_ROOT / DEFAULT_FONT
    fields = []
    for i, (bx, by, bw, bh, _) in enumerate(text_boxes[:2]):
        field_id = "name" if i == 0 else "surname"
        text = name if field_id == "name" else surname
        font_size = max(8, int(bh * 1.1))
        anchor = text_anchor_from_box((bx, by, bw, bh), text or "Аа", font_path, font_size)
        fields.append({
            "id": field_id,
            "label": "Имя" if field_id == "name" else "Фамилия",
            "anchor": anchor,
            "align": "left",
            "font": "assets/Montserrat.ttf",
            "font_size": font_size,
            "color": [0, 0, 0],
            "max_width": bw,
            "auto_shrink": True,
            "uppercase": False,
        })

    if photo_box is None:
        photo_cfg = {
            "place_on_badge": [0, 0, 1290, 1470],
            "crop_size": [1290, 1470],
            "face_scale": DEFAULT_FACE_SCALE,
            "face_offset_y": DEFAULT_FACE_OFFSET_Y,
            "remove_background": False,
        }
    else:
        px, py, pw, ph = photo_box[:4]
        photo_cfg = {
            "place_on_badge": [px, py, pw, ph],
            "crop_size": [pw, ph],
            "face_scale": DEFAULT_FACE_SCALE,
            "face_offset_y": DEFAULT_FACE_OFFSET_Y,
            "remove_background": False,
        }

    return {
        "template_file": template_path.name,
        "badge_size_mm": [100, 70],
        "dpi": 300,
        "text_fields": fields,
        "photo": photo_cfg,
    }


def save_config(config: dict, template_path: Path, out: Path | None = None) -> Path:
    """Сохраняет конфиг в JSON (по умолчанию рядом с макетом)."""
    out = Path(out) if out else Path(template_path).with_suffix(".json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("template", type=Path, help="путь к макету (пустому)")
    parser.add_argument("ready_badge", type=Path, help="путь к готовому бейджу")
    parser.add_argument("--out", type=Path, default=None,
                        help="куда сохранить конфиг (по умолчанию рядом с макетом)")
    args = parser.parse_args()

    try:
        config = generate_config(args.template, args.ready_badge)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1

    out = save_config(config, args.template, args.out)
    print(f"Область фото: {config['photo']['place_on_badge']}")
    for f in config["text_fields"]:
        print(f"Текст «{f['id']}»: якорь={f['anchor']} размер≈{f['font_size']}")
    print(f"\nКонфиг сохранён: {out}")
    print("Проверьте его в мастере настройки шаблона: порядок полей (верхнее "
          "считается именем), размер шрифта и размер бейджа в мм.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
