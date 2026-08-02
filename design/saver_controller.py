"""Контроллер сохранения: PNG по отдельности или PDF для печати с линиями отреза."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from typing import List

from PIL import Image
from PySide6 import QtCore, QtWidgets

from badge_generator.BadgeGenerator import READY_BADGES_DIR, Badge
from design.pdf_output import build_pdf_pages, compute_grid, images_to_pdf
from design.pixmap_utils import pil_to_pixmap
from design.saver import Ui_MainWindow


class Saver(QtWidgets.QMainWindow):
    """Окно сохранения: отдельные файлы или PDF для печати."""

    restarted = QtCore.Signal()

    def __init__(self, badges: List[Badge]):
        super(Saver, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.badges = badges
        template = badges[0].get_template()
        self._badge_size_mm = template.badge_size_mm
        self._dpi = template.dpi

        self.ui.edit_output_dir.setText(str(READY_BADGES_DIR))
        self.ui.label_info.setText(
            f"Бейджей: {len(badges)} · размер бейджа {self._badge_size_mm[0]}×"
            f"{self._badge_size_mm[1]} мм @ {self._dpi} dpi")

        self.ui.btn_browse.clicked.connect(self._browse)
        self.ui.btn_save_separate.clicked.connect(self.save_separate)
        self.ui.btn_save_pdf.clicked.connect(self.save_pdf)
        self.ui.btn_start_over.clicked.connect(self.restarted.emit)
        self.ui.check_cut_lines.toggled.connect(self.update_preview)

        self.update_preview()

    # ------------------------------------------------------------------ #
    def _output_dir(self) -> Path:
        return Path(self.ui.edit_output_dir.text().strip() or str(READY_BADGES_DIR))

    def _browse(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения", str(self._output_dir()))
        if directory:
            self.ui.edit_output_dir.setText(directory)

    # ------------------------------------------------------------------ #
    def update_preview(self) -> None:
        """Показывает первую страницу PDF с текущими настройками."""
        cols, rows = compute_grid(self._badge_size_mm, dpi=self._dpi)
        images = [b.get_photo() for b in self.badges][:cols * rows]
        pages = build_pdf_pages(images, badge_size_mm=self._badge_size_mm, dpi=self._dpi,
                                cut_lines=self.ui.check_cut_lines.isChecked())
        if not pages:
            self.ui.label_preview.setText("Нет бейджей для предпросмотра")
            return
        preview = pages[0].copy()
        preview.thumbnail((600, 400), Image.Resampling.LANCZOS)
        self.ui.label_preview.setPixmap(pil_to_pixmap(preview))

    # ------------------------------------------------------------------ #
    def save_separate(self) -> None:
        output_dir = self._output_dir()
        saved = 0
        try:
            for badge in self.badges:
                badge.save_badge(output_dir)
                saved += 1
        except OSError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файлы:\n{e}")
            return
        self.ui.label_status.setText(
            f"Сохранено {saved} файлов в {output_dir}")

    def save_pdf(self) -> None:
        images = [b.get_photo() for b in self.badges]
        output_dir = self._output_dir()
        path = output_dir / "badges_list.pdf"
        try:
            result = images_to_pdf(images, path, badge_size_mm=self._badge_size_mm,
                                   dpi=self._dpi,
                                   cut_lines=self.ui.check_cut_lines.isChecked())
        except OSError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить PDF:\n{e}")
            return
        if result is None:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Нет бейджей для сохранения.")
            return
        self.ui.label_status.setText(f"PDF сохранён: {result}")
        QtWidgets.QMessageBox.information(
            self, "Готово",
            f"PDF для печати сохранён:\n{result}\n\n"
            "Пунктирные линии — границы бейджей для разрезания.")
