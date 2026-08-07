"""Тест CLI-утилиты сборки PDF из PNG (tools/pngs_to_pdf.py)."""
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent
CLI = ROOT / "tools" / "pngs_to_pdf.py"


def _make_png(path: Path, color: tuple) -> None:
    Image.new("RGB", (1181, 827), color).save(path)


def test_pngs_to_pdf_cli(tmp_path) -> None:
    pngs = []
    for i, color in enumerate([(200, 30, 30), (30, 200, 30), (30, 30, 200)], start=1):
        p = tmp_path / f"badge{i}.png"
        _make_png(p, color)
        pngs.append(p)
    out = tmp_path / "out.pdf"

    result = subprocess.run(
        [sys.executable, str(CLI), str(out), *(str(p) for p in pngs),
         "--badge-mm", "100x70", "--dpi", "300"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.is_file()
    data = out.read_bytes()
    assert data.startswith(b"%PDF")


def test_pngs_to_pdf_cli_without_cut_lines(tmp_path) -> None:
    p = tmp_path / "b.png"
    _make_png(p, (10, 20, 30))
    out = tmp_path / "no_cut.pdf"
    result = subprocess.run(
        [sys.executable, str(CLI), str(out), str(p), "--no-cut-lines"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.is_file()


def test_pngs_to_pdf_cli_bad_size_rejected(tmp_path) -> None:
    p = tmp_path / "b.png"
    _make_png(p, (10, 20, 30))
    result = subprocess.run(
        [sys.executable, str(CLI), str(tmp_path / "x.pdf"), str(p),
         "--badge-mm", "oops"],
        capture_output=True, text=True)
    assert result.returncode != 0
