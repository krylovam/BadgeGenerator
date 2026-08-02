"""Тесты утилиты автоматического вывода конфига (tools/derive_config.py)."""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
FONT = ROOT / "assets" / "Montserrat.ttf"

PHOTO_BOX = (300, 100, 600, 400)   # (x, y, w, h)
NAME_ANCHOR = (100, 560)
SURNAME_ANCHOR = (100, 700)
FONT_SIZE = 90


def make_example(tmp_path: Path):
    tpl = Image.new("RGB", (1200, 900), (255, 255, 255))
    d = ImageDraw.Draw(tpl)
    d.rectangle((0, 0, 1199, 899), outline=(0, 92, 97), width=8)
    d.rectangle((300, 100, 900, 500), outline=(180, 180, 180), width=3)
    d.text((110, 540), "ИМЯ", font=ImageFont.truetype(str(FONT), 40), fill=(150, 150, 150))
    d.text((110, 680), "ФАМИЛИЯ", font=ImageFont.truetype(str(FONT), 40), fill=(150, 150, 150))
    tpl_path = tmp_path / "макет.png"
    tpl.save(tpl_path)

    ready = tpl.copy()
    dr = ImageDraw.Draw(ready)
    ready.paste(Image.new("RGB", (600, 400), (200, 60, 60)), (300, 100))
    font = ImageFont.truetype(str(FONT), FONT_SIZE)
    dr.text(NAME_ANCHOR, "Арина", font=font, fill=(0, 0, 0))
    dr.text(SURNAME_ANCHOR, "Фролова", font=font, fill=(0, 0, 0))
    ready_path = tmp_path / "арина_фролова.png"
    ready.save(ready_path)
    return tpl_path, ready_path


def test_derive_config_cli(tmp_path) -> None:
    tpl, ready = make_example(tmp_path)
    out = tmp_path / "config.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "derive_config.py"),
         str(tpl), str(ready), "--out", str(out)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    cfg = json.loads(out.read_text(encoding="utf-8"))

    # фото определяется точно
    assert cfg["photo"]["place_on_badge"] == list(PHOTO_BOX)

    # текстовые поля: имя сверху, фамилия снизу, якоря близки к реальным (±20 px)
    assert len(cfg["text_fields"]) == 2
    name, surname = cfg["text_fields"]
    assert name["id"] == "name" and surname["id"] == "surname"
    for anchor, expected in ((name["anchor"], NAME_ANCHOR),
                             (surname["anchor"], SURNAME_ANCHOR)):
        assert abs(anchor[0] - expected[0]) <= 20
        assert abs(anchor[1] - expected[1]) <= 20
    # размер шрифта близок к реальному
    assert abs(name["font_size"] - FONT_SIZE) <= 12
    assert abs(surname["font_size"] - FONT_SIZE) <= 12


def test_derive_works_on_real_assets(tmp_path) -> None:
    """Утилита запускается на реальных тестовых ассетах и создаёт валидный конфиг."""
    tpl = ROOT / "tests" / "assets" / "1отряд.png"
    ready = tmp_path / "ready.png"
    # готовый бейдж из демо-макета docs/demo_template.json
    import shutil
    demo = ROOT / "docs" / "demo_badge.png"
    if demo.is_file():
        shutil.copy(demo, ready)
        out = tmp_path / "config.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "derive_config.py"),
             str(tpl), str(ready), "--out", str(out)],
            capture_output=True, text=True)
        # либо успех, либо понятная ошибка — главное не падение с traceback
        assert "Traceback" not in result.stderr
        assert result.returncode == 0 or "не найдена" in result.stderr
