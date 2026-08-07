"""Дымовые тесты интерфейса (offscreen): окна создаются и работают без экрана.

Пропускаются, если PySide6 недоступен в окружении.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

try:
    from PySide6 import QtWidgets
except ImportError:
    pytest.skip("PySide6 недоступен", allow_module_level=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from badge_generator.template import BadgeTemplate  # noqa: E402
from design.constructor_controller import Constructor  # noqa: E402
from design.main_menu import MainMenu  # noqa: E402
from design.saver_controller import Saver  # noqa: E402
from design.template_wizard import TemplateWizard  # noqa: E402

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
TEMPLATE = os.path.join(ASSETS, "1отряд.png")
PHOTOS_DIR = os.path.join(ASSETS, "photos")


@pytest.fixture(scope="module")
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_main_menu(app) -> None:
    menu = MainMenu()
    assert not menu.is_ready()
    # имитация выбора папки и шаблона
    menu._photos = [os.path.join(PHOTOS_DIR, f) for f in os.listdir(PHOTOS_DIR)
                    if f.lower().endswith((".jpeg", ".jpg", ".png"))]
    menu._template_path = os.path.abspath(TEMPLATE)
    menu._load_template_config()
    menu.check_errors()
    assert menu.is_ready()
    assert menu.ui.pushButton_next.isEnabled()
    # новые кнопки: пример бейджа и быстрая настройка
    assert menu.ui.pushButton_preview_example.isEnabled()
    assert menu.ui.pushButton_quick_config.isEnabled()
    menu.toggle_example_badge()
    assert menu._showing_example
    menu.toggle_example_badge()
    assert not menu._showing_example
    menu.close()


def test_constructor_and_saver(app) -> None:
    template = BadgeTemplate.from_template_file(TEMPLATE)
    photos = [os.path.join(PHOTOS_DIR, "judy_estrin.jpeg"),
              os.path.join(PHOTOS_DIR, "tim_oreilly.jpeg")]
    constructor = Constructor(photos, template)
    assert constructor.is_ready()
    assert len(constructor.badges) == 2
    constructor._translate(10, 0)
    constructor._zoom(1.05)
    constructor.undo()
    constructor.next_badge()
    constructor.prev_badge()
    constructor.apply_names()
    assert constructor.badge.get_name() != ""

    saver = Saver(constructor.badges)
    saver.update_preview()
    assert saver.ui.label_preview.pixmap() is not None
    constructor.close()
    saver.close()


def test_template_wizard_saves_config(app, tmp_path) -> None:
    import shutil
    png = tmp_path / "макет.png"
    shutil.copy(TEMPLATE, png)
    wizard = TemplateWizard(png)
    # двигаем поле и фото, сохраняем
    name_field = wizard.template.get_text_field("name")
    assert name_field is not None
    name_field.anchor = (50, 60)
    wizard.template.photo.place_on_badge = (10, 20, 300, 400)
    path = wizard.template.save_json()
    assert path.is_file()
    loaded = BadgeTemplate.from_json(path)
    assert loaded.get_text_field("name").anchor == (50, 60)
    assert loaded.photo.place_on_badge == (10, 20, 300, 400)
    wizard.close()
