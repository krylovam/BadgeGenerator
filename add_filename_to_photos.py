#!/usr/bin/env python3
"""Добавляет к фотографиям белые поля и подпись с именем файла."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jfif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
DEFAULT_FONT = Path(__file__).resolve().parent / "assets" / "Montserrat.ttf"


def positive_int(value: str) -> int:
    """Проверка положительного целого числа для argparse."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("значение должно быть больше нуля")
    return number


def non_negative_int(value: str) -> int:
    """Проверка неотрицательного целого числа для argparse."""
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("значение не может быть отрицательным")
    return number


def find_photos(input_dir: Path, recursive: bool = False) -> Iterable[Path]:
    """Возвращает поддерживаемые изображения в стабильном порядке."""
    paths = input_dir.rglob("*") if recursive else input_dir.iterdir()
    return sorted(
        (path for path in paths if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS),
        key=lambda path: str(path).lower(),
    )


def _is_inside(path: Path, directory: Path) -> bool:
    """Проверяет, находится ли путь внутри указанной папки."""
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def add_caption(
    source: Path,
    destination: Path,
    font_path: Path = DEFAULT_FONT,
    margin: Optional[int] = None,
    font_size: Optional[int] = None,
) -> None:
    """Создаёт копию фотографии с полями и подписью из имени файла."""
    with Image.open(source) as opened_image:
        image_format = opened_image.format
        image = ImageOps.exif_transpose(opened_image).convert("RGB")
        icc_profile = opened_image.info.get("icc_profile")
        dpi = opened_image.info.get("dpi")

    width, height = image.size
    actual_margin = margin if margin is not None else max(20, round(min(width, height) * 0.03))
    actual_font_size = font_size if font_size is not None else max(
        18, round(min(width, height) * 0.05)
    )

    font = ImageFont.truetype(str(font_path), size=actual_font_size)
    caption = source.stem

    # textbbox учитывает выступы символов относительно точки отрисовки.
    measuring_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_bbox = measuring_draw.textbbox((0, 0), caption, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Для очень длинного имени расширяем поля, а не обрезаем подпись.
    canvas_width = max(width + 2 * actual_margin, text_width + 2 * actual_margin)
    canvas_height = height + text_height + 3 * actual_margin
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")

    photo_x = (canvas_width - width) // 2
    canvas.paste(image, (photo_x, actual_margin))

    text_x = (canvas_width - text_width) // 2 - text_bbox[0]
    text_y = actual_margin + height + actual_margin - text_bbox[1]
    ImageDraw.Draw(canvas).text((text_x, text_y), caption, font=font, fill="black")

    destination.parent.mkdir(parents=True, exist_ok=True)
    save_options = {}
    if icc_profile:
        save_options["icc_profile"] = icc_profile
    if dpi:
        save_options["dpi"] = dpi
    if image_format in {"JPEG", "WEBP"}:
        save_options["quality"] = 95
    if image_format == "JPEG":
        save_options["optimize"] = True

    canvas.save(destination, format=image_format, **save_options)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Добавляет к каждому фото белые поля и печатает снизу имя файла "
            "без расширения. Исходные фотографии не изменяются."
        )
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="папка с фотографиями (по умолчанию текущая папка)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="папка результата (по умолчанию <имя папки>_with_names рядом с исходной)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="обрабатывать также фотографии во вложенных папках",
    )
    parser.add_argument(
        "--margin",
        type=non_negative_int,
        help="размер поля в пикселях (по умолчанию 3%% от меньшей стороны)",
    )
    parser.add_argument(
        "--font-size",
        type=positive_int,
        help="размер шрифта в пикселях (по умолчанию 5%% от меньшей стороны)",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=DEFAULT_FONT,
        help="путь к файлу шрифта TTF/OTF",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    input_dir = args.input_dir.expanduser().resolve()

    if not input_dir.is_dir():
        print(f"Ошибка: папка не найдена: {input_dir}", file=sys.stderr)
        return 2

    font_path = args.font.expanduser().resolve()
    if not font_path.is_file():
        print(f"Ошибка: шрифт не найден: {font_path}", file=sys.stderr)
        return 2

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else input_dir.parent / f"{input_dir.name}_with_names"
    )
    if output_dir == input_dir:
        print("Ошибка: папка результата должна отличаться от исходной.", file=sys.stderr)
        return 2

    photos = list(find_photos(input_dir, recursive=args.recursive))
    if args.recursive:
        # Не обрабатываем повторно результаты прошлого запуска, если пользователь
        # явно поместил папку результата внутрь исходной папки.
        try:
            output_dir.relative_to(input_dir)
        except ValueError:
            pass
        else:
            photos = [
                photo
                for photo in photos
                if not _is_inside(photo, output_dir)
            ]

    if not photos:
        print(f"В папке {input_dir} не найдено поддерживаемых изображений.")
        return 0

    completed = 0
    failed = 0
    for source in photos:
        relative_path = source.relative_to(input_dir)
        destination = output_dir / relative_path
        try:
            add_caption(
                source,
                destination,
                font_path=font_path,
                margin=args.margin,
                font_size=args.font_size,
            )
            completed += 1
            print(f"Готово: {destination}")
        except (OSError, ValueError, UnidentifiedImageError) as error:
            failed += 1
            print(f"Не удалось обработать {source}: {error}", file=sys.stderr)

    print(f"\nОбработано: {completed}. Ошибок: {failed}. Результат: {output_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
