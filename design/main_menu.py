"""Главное меню: выбор папки с фото, макета бейджа и его конфигурации."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Signal

from badge_generator.template import BadgeTemplate, TemplateConfigError
from design.pixmap_utils import load_pixmap
from design.ui_main_menu import Ui_MainWindow

UI_PATH = Path(__file__).resolve().parent / "main_menu.ui"
PHOTO_TYPES = ("*.png", "*.jpeg", "*.jpg", "*.PNG", "*.JPEG", "*.JPG")


class MainMenu(QtWidgets.QMainWindow):
    """Стартовое окно: выбор данных и переход к конструктору."""

    next_requested = Signal()
    configure_requested = Signal()

    def __init__(self):
        super(MainMenu, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Генератор бейджей")

        self._photos: List[str] = []
        self._template_path: Optional[Path] = None
        self._template: Optional[BadgeTemplate] = None
        self._config_missing = False

        self.ui.pushButton_photos.clicked.connect(self.select_photos)
        self.ui.pushButton_template.clicked.connect(self.select_template)
        self.ui.pushButton_configure.clicked.connect(self.open_template_wizard)
        self.ui.pushButton_next.clicked.connect(self.next_requested.emit)

    # ------------------------------------------------------------------ #
    # Публичное состояние
    # ------------------------------------------------------------------ #
    @property
    def photos(self) -> List[str]:
        return list(self._photos)

    @property
    def template(self) -> Optional[BadgeTemplate]:
        return self._template

    def is_ready(self) -> bool:
        return bool(self._photos) and self._template is not None and not self._config_missing

    # ------------------------------------------------------------------ #
    # Выбор данных
    # ------------------------------------------------------------------ #
    def select_photos(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку с фотографиями")
        if not directory:
            return
        self._photos = []
        folder = Path(directory)
        for pattern in PHOTO_TYPES:
            self._photos.extend(str(p) for p in sorted(folder.glob(pattern)))
        self.ui.label_photos_info.setText(f"Фото: найдено {len(self._photos)}")
        self.check_errors()

    def select_template(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите макет бейджа", "", "Изображения (*.png *.jpg *.jpeg)")
        if not filename:
            return
        self._template_path = Path(filename)
        self._load_template_config()
        self.check_errors()

    def _load_template_config(self) -> None:
        assert self._template_path is not None
        self._config_missing = False
        self._template = None
        try:
            self._template = BadgeTemplate.from_template_file(self._template_path)
            self.ui.label_template_info.setText(
                f"Шаблон: {self._template_path.name} · {self._template.badge_size_mm[0]}×"
                f"{self._template.badge_size_mm[1]} мм @ {self._template.dpi} dpi")
        except TemplateConfigError:
            self._config_missing = True
            self.ui.label_template_info.setText(
                f"Шаблон: {self._template_path.name} — конфиг не найден, нажмите «Настроить шаблон…»")
        self.ui.pushButton_configure.setEnabled(self._template_path is not None)
        self._update_preview()

    def _update_preview(self) -> None:
        if self._template is not None:
            pixmap = load_pixmap(str(self._template.template_file), (460, 320))
            self.ui.label_preview.setPixmap(pixmap)
        else:
            self.ui.label_preview.clear()
            self.ui.label_preview.setText("Макет не выбран")

    def open_template_wizard(self) -> None:
        if self._template_path is None:
            return
        from design.template_wizard import TemplateWizard
        wizard = TemplateWizard(self._template_path, parent=self)
        if wizard.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_template_config()
            self.check_errors()

    def check_errors(self) -> None:
        if not self._photos:
            self.ui.error_label.setText("В выбранной папке нет фотографий (*.png, *.jpg, *.jpeg)")
        elif self._template is None:
            self.ui.error_label.setText("Выберите шаблон и настройте его конфигурацию")
        else:
            self.ui.error_label.setText("")
        self.ui.pushButton_next.setEnabled(self.is_ready())
