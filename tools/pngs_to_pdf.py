#!/usr/bin/env python3
"""Собрать PDF для печати из нескольких PNG-файлов (готовых бейджей).

Примеры:
    python tools/pngs_to_pdf.py out.pdf badge1.png badge2.png badge3.png
    python tools/pngs_to_pdf.py out.pdf *.png --badge-mm 100x70 --no-cut-lines
    python tools/pngs_to_pdf.py out.pdf *.png --badge-mm 90x60 --dpi 300

Параметры:
    --badge-mm ШxВ   размер бейджа в мм (по умолчанию 100x70)
    --dpi N          разрешение печати (по умолчанию 300)
    --margin-mm N    поля листа (по умолчанию 8)
    --gap-mm N       зазор между бейджами (по умолчанию 3)
    --no-cut-lines   не рисовать линии отреза
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from design.pdf_output import images_to_pdf  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Сборка PDF для печати из PNG-файлов бейджей.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", type=Path, help="путь к итоговому PDF")
    parser.add_argument("images", nargs="+", type=Path, help="PNG/JPG-файлы бейджей")
    parser.add_argument("--badge-mm", default="100x70",
                        help="размер бейджа в мм, формат ШxВ (по умолчанию 100x70)")
    parser.add_argument("--dpi", type=int, default=300, help="разрешение печати (по умолчанию 300)")
    parser.add_argument("--margin-mm", type=float, default=8.0, help="поля листа, мм")
    parser.add_argument("--gap-mm", type=float, default=3.0, help="зазор между бейджами, мм")
    parser.add_argument("--no-cut-lines", action="store_true",
                        help="не рисовать линии отреза")
    args = parser.parse_args()

    try:
        w, h = args.badge_mm.lower().split("x")
        badge_size_mm = (float(w), float(h))
    except ValueError:
        parser.error("--badge-mm должен быть в формате ШxВ, например 100x70")

    images = []
    for f in args.images:
        try:
            images.append(Image.open(f).convert("RGB"))
        except OSError as e:
            print(f"Пропущен {f.name}: {e}", file=sys.stderr)
    if not images:
        print("Нет изображений для сборки PDF.", file=sys.stderr)
        return 1

    result = images_to_pdf(images, args.output,
                           badge_size_mm=badge_size_mm,
                           dpi=args.dpi,
                           margins_mm=args.margin_mm,
                           gap_mm=args.gap_mm,
                           cut_lines=not args.no_cut_lines)
    print(f"PDF сохранён: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
