"""Тесты PDF-вывода: формат A4, сетка, линии отреза, порядок бейджей."""
import os

from PIL import Image

from design.pdf_output import (
    A4_MM,
    build_pdf_pages,
    compute_grid,
    images_to_pdf,
    mm_to_px,
)

BADGE_SIZE = (100, 70)  # мм
DPI = 300


def _solid_badge(color: tuple) -> Image.Image:
    """Синтетический бейдж размером 100x70 мм при 300 dpi."""
    return Image.new("RGB", (1181, 827), color)


def test_mm_to_px() -> None:
    assert mm_to_px(100, 300) == 1181  # 100 / 25.4 * 300 = 1181.1


def test_compute_grid() -> None:
    # A4 210x297, поля 8 мм, зазор 3 мм, бейдж 100x70
    cols, rows = compute_grid(BADGE_SIZE, A4_MM, 8, 3, DPI)
    assert cols == 1
    assert rows == 3
    # с максимальным числом на страницу
    cols, rows = compute_grid(BADGE_SIZE, A4_MM, 8, 3, DPI, max_per_page=2)
    assert cols * rows <= 2


def test_page_size_and_count() -> None:
    badges = [_solid_badge((i * 40, 0, 0)) for i in range(1, 7)]
    pages = build_pdf_pages(badges, badge_size_mm=BADGE_SIZE, dpi=DPI, cut_lines=False)
    assert len(pages) == 2  # 6 бейджей, по 3 на страницу (1x3)
    for page in pages:
        assert page.size == (mm_to_px(210, DPI), mm_to_px(297, DPI)) == (2480, 3508)


def test_badge_order_preserved() -> None:
    badges = [_solid_badge((i * 40, 0, 0)) for i in range(1, 4)]
    pages = build_pdf_pages(badges, badge_size_mm=BADGE_SIZE, dpi=DPI, cut_lines=False)
    page = pages[0]
    # первый бейдж — в верхней части страницы, цвет (40, 0, 0)
    assert page.getpixel((page.width // 2, 600)) == (40, 0, 0)
    # второй — ниже
    assert page.getpixel((page.width // 2, 1500)) == (80, 0, 0)


def _first_badge_top_left() -> tuple:
    """Позиция верхнего левого угла первого бейджа на странице (без линии)."""
    page_w, page_h = mm_to_px(210, DPI), mm_to_px(297, DPI)
    badge_w, badge_h = mm_to_px(100, DPI), mm_to_px(70, DPI)
    gap = mm_to_px(3, DPI)
    cols, rows = compute_grid(BADGE_SIZE, A4_MM, 8, 3, DPI)
    grid_w = cols * badge_w + (cols - 1) * gap
    grid_h = rows * badge_h + (rows - 1) * gap
    return (page_w - grid_w) // 2, (page_h - grid_h) // 2


def test_cut_lines_drawn() -> None:
    badges = [_solid_badge((10, 20, 30))]
    pages = build_pdf_pages(badges, badge_size_mm=BADGE_SIZE, dpi=DPI, cut_lines=True)
    page = pages[0]
    bx, by = _first_badge_top_left()
    off = mm_to_px(0.8, DPI)
    x0, y0 = bx - off, by - off
    # в начале штриха — серый цвет линии
    assert page.getpixel((x0, y0)) == (70, 70, 70)
    # штрих идёт, потом промежуток
    dash = mm_to_px(4.0, DPI)
    gap = mm_to_px(2.5, DPI)
    assert page.getpixel((x0 + dash + 3, y0)) == (255, 255, 255)


def test_cut_lines_can_be_disabled() -> None:
    badges = [_solid_badge((10, 20, 30))]
    pages = build_pdf_pages(badges, badge_size_mm=BADGE_SIZE, dpi=DPI, cut_lines=False)
    page = pages[0]
    bx, by = _first_badge_top_left()
    off = mm_to_px(0.8, DPI)
    assert page.getpixel((bx - off, by - off)) == (255, 255, 255)


def test_no_distortion_of_portrait_badge() -> None:
    """Бейдж с пропорциями, отличными от слота, вписывается без искажений."""
    tall = Image.new("RGB", (800, 1200), (200, 100, 50))
    pages = build_pdf_pages([tall], badge_size_mm=BADGE_SIZE, dpi=DPI, cut_lines=False)
    page = pages[0]
    badge_w, badge_h = mm_to_px(100, DPI), mm_to_px(70, DPI)
    bx, by = _first_badge_top_left()
    # вписанное изображение центрировано по горизонтали: слева от него белое поле
    assert page.getpixel((bx + 10, by + badge_h // 2)) == (255, 255, 255)
    # центр слота — цвет бейджа (высота заполнена полностью: 800x1200 -> 551x827)
    assert page.getpixel((bx + badge_w // 2, by + badge_h // 2)) == (200, 100, 50)


def test_images_to_pdf_saves_file(tmp_path) -> None:
    badges = [_solid_badge((5, 5, 5)) for _ in range(4)]
    path = tmp_path / "out" / "badges.pdf"
    result = images_to_pdf(badges, path, badge_size_mm=BADGE_SIZE, dpi=DPI)
    assert result is not None
    assert path.is_file()
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    # 4 бейджа по 3 на страницу -> 2 страницы
    assert data.count(b"/Type /Page") >= 2


def test_empty_input_returns_none(tmp_path) -> None:
    assert images_to_pdf([], tmp_path / "empty.pdf", badge_size_mm=BADGE_SIZE) is None
