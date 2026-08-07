"""Главное меню: выбор папки с фото, макета бейджа и его конфигурации."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Signal

from badge_generator.template import BadgeTemplate, TemplateConfigError
from design.pixmap_utils import load_pixmap, pil_to_pixmap
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
        self._showing_example = False

        self.ui.pushButton_photos.clicked.connect(self.select_photos)
        self.ui.pushButton_template.clicked.connect(self.select_template)
        self.ui.pushButton_configure.clicked.connect(self.open_template_wizard)
        self.ui.pushButton_quick_config.clicked.connect(self.quick_configure_from_ready)
        self.ui.pushButton_preview_example.clicked.connect(self.toggle_example_badge)
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
        self._showing_example = False
        self.ui.pushButton_preview_example.setText("Показать пример бейджа с фото")
        if self._template is not None:
            self.ui.pushButton_preview_example.setEnabled(bool(self._photos))
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
        self._showing_example = False
        self.ui.pushButton_configure.setEnabled(self._template_path is not None)
        self.ui.pushButton_quick_config.setEnabled(self._template_path is not None)
        self.ui.pushButton_preview_example.setEnabled(
            self._template_path is not None and bool(self._photos))
        self.ui.pushButton_preview_example.setText("Показать пример бейджа с фото")
        self._update_preview()

    def _update_preview(self) -> None:
        if self._template is not None:
            pixmap = load_pixmap(str(self._template.template_file), (460, 320))
            self.ui.label_preview.setPixmap(pixmap)
        else:
            self.ui.label_preview.clear()
            self.ui.label_preview.setText("Макет не выбран")

    # ------------------------------------------------------------------ #
    # Пример готового бейджа (превью)
    # ------------------------------------------------------------------ #
    def toggle_example_badge(self) -> None:
        if self._showing_example:
            self._showing_example = False
            self.ui.pushButton_preview_example.setText("Показать пример бейджа с фото")
            self._update_preview()
            return
        if self._template is None or not self._photos:
            self.ui.error_label.setText("Сначала выберите папку с фото и шаблон")
            return
        try:
            from badge_generator.BadgeGenerator import Badge
            badge = Badge(0, self._photos[0], self._template)
            preview = badge.get_preview_image((460, 320))
        except Exception as e:  # noqa: BLE001
            self.ui.error_label.setText(f"Не удалось построить пример: {e}")
            return
        self.ui.label_preview.setPixmap(pil_to_pixmap(preview))
        self.ui.pushButton_preview_example.setText("Показать макет")
        self._showing_example = True
        self.ui.error_label.setText(
            f"Пример: {Path(self._photos[0]).name} — имя/фамилия из названия файла")

    # ------------------------------------------------------------------ #
    # Быстрая настройка по готовому бейджу
    # ------------------------------------------------------------------ #
    def quick_configure_from_ready(self) -> None:
        """Создаёт конфиг шаблона, сравнив макет и готовый бейдж."""
        if self._template_path is None:
            return
        ready, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите готовый бейдж (пример результата)",
            "", "Изображения (*.png *.jpg *.jpeg)")
        if not ready:
            return
        from tools.derive_config import generate_config, save_config
        try:
            config = generate_config(self._template_path, Path(ready))
            out = save_config(config, self._template_path)
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Не удалось настроить", str(e))
            return
        except Exception as e:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Не удалось настроить", f"Ошибка: {e}")
            return
        self._load_template_config()
        self.check_errors()
        QtWidgets.QMessageBox.information(
            self, "Готово",
            f"Конфиг создан: {out}\n\nОпределены координаты текста и фото. "
            "Откройте «Настроить шаблон…», чтобы проверить и поправить детали.")

    def open_template_wizard(self) -> None:
        if self._template_path is None:
            return
        from design.template_wizard import TemplateWizard
        try:
            wizard = TemplateWizard(self._template_path, photos=self._photos, parent=self)
        except Exception as e:  # noqa: BLE001 — показываем ошибку, а не «молчим»
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "Не удалось открыть настройку шаблона",
                f"Произошла ошибка:\n{e}\n\nПодробности в консоли.")
            return
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
        self.ui.pushButton_preview_example.setEnabled(
            self._template_path is not None and bool(self._photos))
