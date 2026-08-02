"""Сборка PDF для печати: A4, реальные размеры бейджа, линии отреза.

Размер бейджа задаётся в миллиметрах (берётся из конфига шаблона),
печать — в 300 dpi, пропорции изображений всегда сохраняются.
Вокруг каждого бейджа рисуется пунктирная линия отреза.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

A4_MM = (210, 297)
DEFAULT_DPI = 300
DEFAULT_MARGIN_MM = 8.0
DEFAULT_GAP_MM = 3.0
CUT_LINE_OFFSET_MM = 0.8   # отступ линии отреза наружу, чтобы не срезать бейдж
DASH_LENGTH_MM = 4.0       # длина штриха
GAP_LENGTH_MM = 2.5        # длина промежутка
CUT_LINE_COLOR = (70, 70, 70)
CUT_LINE_WIDTH = 2


def mm_to_px(mm: float, dpi: int = DEFAULT_DPI) -> int:
    return round(mm / 25.4 * dpi)


def compute_grid(badge_size_mm: Tuple[float, float],
                 page_size_mm: Tuple[float, float] = A4_MM,
                 margins_mm: float = DEFAULT_MARGIN_MM,
                 gap_mm: float = DEFAULT_GAP_MM,
                 dpi: int = DEFAULT_DPI,
                 max_per_page: Optional[int] = None) -> Tuple[int, int]:
    """Считает, сколько бейджей (колонки x строки) влезает на страницу."""
    page_w = mm_to_px(page_size_mm[0], dpi)
    page_h = mm_to_px(page_size_mm[1], dpi)
    margin = mm_to_px(margins_mm, dpi)
    gap = mm_to_px(gap_mm, dpi)
    badge_w = mm_to_px(badge_size_mm[0], dpi)
    badge_h = mm_to_px(badge_size_mm[1], dpi)
    avail_w = page_w - 2 * margin
    avail_h = page_h - 2 * margin
    cols = max(1, (avail_w + gap) // (badge_w + gap))
    rows = max(1, (avail_h + gap) // (badge_h + gap))
    if max_per_page is not None and max_per_page > 0:
        # сначала уменьшаем число колонок, затем строк
        while cols * rows > max_per_page and cols > 1:
            cols -= 1
        while cols * rows > max_per_page and rows > 1:
            rows -= 1
        if cols * rows > max_per_page:
            cols, rows = max(1, max_per_page), 1
    return int(cols), int(rows)


def _fit_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Вписывает изображение в слот (width x height) без искажения пропорций."""
    img = image.convert("RGB")
    img.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "white")
    x = (width - img.width) // 2
    y = (height - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def _draw_dashed_line(draw: ImageDraw.ImageDraw, p0: Tuple[float, float],
                      p1: Tuple[float, float], dash: int, gap: int,
                      fill: Tuple[int, int, int], width: int) -> None:
    x0, y0 = p0
    x1, y1 = p1
    length = math.hypot(x1 - x0, y1 - y0)
    if length == 0:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
        end = min(pos + dash, length)
        draw.line((x0 + ux * pos, y0 + uy * pos, x0 + ux * end, y0 + uy * end),
                  fill=fill, width=width)
        pos = end + gap


def draw_dashed_rect(draw: ImageDraw.ImageDraw, box: Tuple[int, int, int, int],
                     dash: int = 24, gap: int = 14,
                     fill: Tuple[int, int, int] = CUT_LINE_COLOR,
                     width: int = CUT_LINE_WIDTH) -> None:
    """Пунктирный прямоугольник (линия отреза) вокруг бейджа."""
    x0, y0, x1, y1 = box
    edges = (
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    )
    for a, b in edges:
        _draw_dashed_line(draw, a, b, dash, gap, fill, width)


def build_pdf_pages(images: Sequence[Image.Image],
                    badge_size_mm: Tuple[float, float] = (100, 70),
                    dpi: int = DEFAULT_DPI,
                    page_size_mm: Tuple[float, float] = A4_MM,
                    margins_mm: float = DEFAULT_MARGIN_MM,
                    gap_mm: float = DEFAULT_GAP_MM,
                    cut_lines: bool = True,
                    max_per_page: Optional[int] = None) -> List[Image.Image]:
    """Собирает страницы PDF (без сохранения) — можно использовать для предпросмотра."""
    page_w = mm_to_px(page_size_mm[0], dpi)
    page_h = mm_to_px(page_size_mm[1], dpi)
    badge_w = mm_to_px(badge_size_mm[0], dpi)
    badge_h = mm_to_px(badge_size_mm[1], dpi)
    gap = mm_to_px(gap_mm, dpi)
    cols, rows = compute_grid(badge_size_mm, page_size_mm, margins_mm, gap_mm, dpi, max_per_page)
    per_page = cols * rows

    prepared = [_fit_image(img, badge_w, badge_h) for img in images]
    pages: List[Image.Image] = []
    for start in range(0, len(prepared), per_page):
        page = Image.new("RGB", (page_w, page_h), "white")
        draw = ImageDraw.Draw(page)
        block = prepared[start:start + per_page]
        grid_w = cols * badge_w + (cols - 1) * gap
        grid_h = rows * badge_h + (rows - 1) * gap
        offset_x = (page_w - grid_w) // 2
        offset_y = (page_h - grid_h) // 2
        cut_offset = mm_to_px(CUT_LINE_OFFSET_MM, dpi)
        dash = mm_to_px(DASH_LENGTH_MM, dpi)
        dash_gap = mm_to_px(GAP_LENGTH_MM, dpi)
        for i, img in enumerate(block):
            row, col = divmod(i, cols)
            x = offset_x + col * (badge_w + gap)
            y = offset_y + row * (badge_h + gap)
            page.paste(img, (x, y))
            if cut_lines:
                draw_dashed_rect(draw, (x - cut_offset, y - cut_offset,
                                        x + badge_w + cut_offset, y + badge_h + cut_offset),
                                 dash=dash, gap=dash_gap)
        pages.append(page)
    return pages


def images_to_pdf(images_list: Sequence[Image.Image], path_to_upload,
                  badge_size_mm: Tuple[float, float] = (100, 70),
                  dpi: int = DEFAULT_DPI,
                  page_size_mm: Tuple[float, float] = A4_MM,
                  margins_mm: float = DEFAULT_MARGIN_MM,
                  gap_mm: float = DEFAULT_GAP_MM,
                  cut_lines: bool = True,
                  max_per_page: Optional[int] = None) -> Optional[Path]:
    """Сохраняет бейджи в многостраничный PDF. Возвращает путь к файлу."""
    pages = build_pdf_pages(list(images_list), badge_size_mm=badge_size_mm, dpi=dpi,
                            page_size_mm=page_size_mm, margins_mm=margins_mm,
                            gap_mm=gap_mm, cut_lines=cut_lines, max_per_page=max_per_page)
    if not pages:
        return None
    path = Path(path_to_upload)
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=dpi)
    return path
