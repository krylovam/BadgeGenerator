#!/usr/bin/env python3
"""Собрать PDF для печати из списка URL: каждый URL -> QR-код.

QR-коды раскладываются на страницах A4 (300 dpi) с заданным размером,
пунктирными линиями отреза и подписью под каждым кодом (по умолчанию —
порядковый номер, можно URL).

Примеры:
    python tools/urls_to_qr_pdf.py urls.txt qr.pdf
    python tools/urls_to_qr_pdf.py urls.txt qr.pdf --qr-mm 30 --label url
    python tools/urls_to_qr_pdf.py https://a.ru https://b.ru out.pdf

Формат файла urls.txt: по одному URL (или тексту) на строку, пустые строки
и строки с # игнорируются.

Параметры:
    --qr-mm N       размер QR-кода в мм (по умолчанию 30)
    --label none|num|url   что писать под QR (по умолчанию num)
    --dpi N         разрешение печати (по умолчанию 300)
    --margin-mm N   поля листа (по умолчанию 8)
    --gap-mm N      зазор между QR (по умолчанию 3)
    --no-cut-lines  не рисовать линии отреза
    --max-per-page N  ограничить число QR на странице
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from design.pdf_output import images_to_pdf, mm_to_px  # noqa: E402

LABEL_FONT = "assets/Montserrat.ttf"
LABEL_FONT_SIZE = 24  # px при 300 dpi (~2 мм)
LABEL_PADDING_PX = 20


def _make_qr_image(url: str, size_px: int, quiet_zone: int = 2) -> Image.Image:
    """Генерирует QR-код для url размером size_px (с тихой зоной)."""
    import qrcode
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=quiet_zone,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size_px, size_px), Image.Resampling.LANCZOS)


def _make_qr_with_label(url: str, size_px: int, label: str,
                        font: ImageFont.FreeTypeFont) -> Image.Image:
    """QR-код с подписью под ним (белая полоса с текстом)."""
    label_h = font.size + LABEL_PADDING_PX * 2
    canvas = Image.new("RGB", (size_px, size_px + label_h), "white")
    qr = _make_qr_image(url, size_px)
    canvas.paste(qr, (0, 0))
    if label:
        draw = ImageDraw.Draw(canvas)
        # подпись по центру под QR
        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        tw = right - left
        x = (size_px - tw) // 2
        y = size_px + LABEL_PADDING_PX
        draw.text((x, y), label, font=font, fill=(0, 0, 0))
    return canvas


def build_qr_pages(urls, qr_size_px, label_mode, font, dpi, margins_mm, gap_mm,
                   cut_lines, max_per_page):
    """Собирает страницы (PIL Image) с QR-кодами и линиями отреза."""
    from design.pdf_output import build_pdf_pages, compute_grid

    # размер QR в мм (квадрат)
    qr_mm = qr_size_px / dpi * 25.4

    images = []
    for i, url in enumerate(urls):
        if label_mode == "none":
            label = ""
        elif label_mode == "url":
            label = url if len(url) <= 48 else url[:45] + "..."
        else:
            label = str(i + 1)
        images.append(_make_qr_with_label(url, qr_size_px, label, font))

    # у нас уже готовые изображения QR (с подписью) — используем build_pdf_pages,
    # передавая размер слотов = размер QR + подпись
    label_h = font.size + LABEL_PADDING_PX * 2
    slot_mm = (qr_mm, qr_mm + label_h / dpi * 25.4)
    return build_pdf_pages(images, badge_size_mm=slot_mm, dpi=dpi,
                           margins_mm=margins_mm, gap_mm=gap_mm,
                           cut_lines=cut_lines, max_per_page=max_per_page)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Сборка PDF с QR-кодами из списка URL для печати.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="+", help="файл с URL (по одному на строку) или сами URL")
    parser.add_argument("output", type=Path, help="путь к итоговому PDF")
    parser.add_argument("--qr-mm", type=float, default=30.0,
                        help="размер QR-кода в мм (по умолчанию 30)")
    parser.add_argument("--label", choices=["none", "num", "url"], default="num",
                        help="подпись под QR: номер / URL / ничего (по умолчанию num)")
    parser.add_argument("--dpi", type=int, default=300, help="разрешение печати (по умолчанию 300)")
    parser.add_argument("--margin-mm", type=float, default=8.0, help="поля листа, мм")
    parser.add_argument("--gap-mm", type=float, default=3.0, help="зазор между QR, мм")
    parser.add_argument("--no-cut-lines", action="store_true", help="не рисовать линии отреза")
    parser.add_argument("--max-per-page", type=int, default=0,
                        help="ограничить число QR на странице (0 = авто)")
    args = parser.parse_args()

    # собираем список URL: если аргумент — существующий файл, читаем построчно
    urls = []
    for arg in args.urls:
        p = Path(arg)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        elif p.suffix.lower() in (".txt", ".csv", ".list"):
            # явно текстовый файл, но его нет — ошибка
            print(f"Файл не найден: {arg}", file=sys.stderr)
            return 1
        else:
            urls.append(arg)
    if not urls:
        print("Нет URL для генерации.", file=sys.stderr)
        return 1

    from badge_generator.template import resolve_font_path, PROJECT_ROOT
    font_path = resolve_font_path(LABEL_FONT, PROJECT_ROOT)
    font = ImageFont.truetype(str(font_path), size=LABEL_FONT_SIZE)

    qr_size_px = mm_to_px(args.qr_mm, args.dpi)
    pages = build_qr_pages(urls, qr_size_px, args.label, font,
                           args.dpi, args.margin_mm, args.gap_mm,
                           not args.no_cut_lines, args.max_per_page)

    # сохраняем через images_to_pdf (тот же путь, что и у бейджей)
    from design.pdf_output import images_to_pdf
    # изображения уже собраны в pages — сохраняем их напрямую
    if not pages:
        print("Нет QR для сохранения.", file=sys.stderr)
        return 1
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=args.dpi)
    print(f"PDF сохранён: {out} ({len(pages)} стр., {len(urls)} QR)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
