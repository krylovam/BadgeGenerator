"""Тест генерации PDF с QR-кодами (tools/urls_to_qr_pdf.py)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
CLI = ROOT / "tools" / "urls_to_qr_pdf.py"

qrcode = pytest.importorskip("qrcode")


def test_urls_to_qr_pdf_cli(tmp_path) -> None:
    urls = tmp_path / "urls.txt"
    urls.write_text(
        "https://example.com/1\n"
        "https://example.com/2\n"
        "\n"
        "# комментарий\n"
        "https://example.com/3\n",
        encoding="utf-8")
    out = tmp_path / "qr.pdf"
    result = subprocess.run(
        [sys.executable, str(CLI), str(urls), str(out),
         "--qr-mm", "30", "--label", "num"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    data = out.read_bytes()
    assert data.startswith(b"%PDF")


def test_qr_page_layout(tmp_path) -> None:
    """QR-коды раскладываются по сетке, линии отреза рисуются."""
    sys.path.insert(0, str(ROOT))
    from PIL import ImageFont

    from badge_generator.template import PROJECT_ROOT, resolve_font_path
    from design.pdf_output import mm_to_px
    from tools.urls_to_qr_pdf import LABEL_FONT, LABEL_FONT_SIZE, build_qr_pages

    font = ImageFont.truetype(str(resolve_font_path(LABEL_FONT, PROJECT_ROOT)),
                              size=LABEL_FONT_SIZE)
    pages = build_qr_pages(
        ["https://example.com/1"] * 4,
        mm_to_px(30, 300), "num", font, 300, 8, 3, True, 0)
    assert len(pages) == 1
    page = pages[0]
    assert page.size == (2480, 3508)  # A4 @300dpi
    # позиция первого QR: сетка центрируется
    label_h_px = LABEL_FONT_SIZE + 40
    qr_px = mm_to_px(30, 300)
    slot_mm = (30, 30 + label_h_px / 300 * 25.4)
    from design.pdf_output import compute_grid, A4_MM
    cols, rows = compute_grid(slot_mm, A4_MM, 8, 3, 300)
    badge_w = mm_to_px(slot_mm[0], 300)
    badge_h = mm_to_px(slot_mm[1], 300)
    gap = mm_to_px(3, 300)
    grid_w = cols * badge_w + (cols - 1) * gap
    grid_h = rows * badge_h + (rows - 1) * gap
    offset_x = (2480 - grid_w) // 2
    offset_y = (3508 - grid_h) // 2
    off = mm_to_px(0.8, 300)
    # линия отреза чуть левее/выше первого QR
    assert page.getpixel((offset_x - off, offset_y - off))[:3] == (70, 70, 70), \
        "нет линии отреза"
    # внутри QR-слота — есть тёмные пиксели (QR нарисован)
    dark = 0
    for px in range(offset_x + 10, offset_x + qr_px - 10, 20):
        for py in range(offset_y + 10, offset_y + qr_px - 10, 20):
            if page.getpixel((px, py))[:3] == (0, 0, 0):
                dark += 1
    assert dark > 10, "QR-модули не найдены на странице"


def test_qr_missing_urls_rejected(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), str(tmp_path / "empty.txt"), str(tmp_path / "x.pdf")],
        capture_output=True, text=True)
    assert result.returncode != 0
