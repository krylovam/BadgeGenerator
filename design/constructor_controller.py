"""Контроллер конструктора: генерация бейджей и правка положения фото."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional, Tuple

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QKeySequence, QShortcut

from badge_generator.BadgeGenerator import Badge
from badge_generator.template import BadgeTemplate
from design.constructor import Ui_MainWindow
from design.pixmap_utils import pil_to_pixmap

HISTORY_LIMIT = 50


class Constructor(QtWidgets.QMainWindow):
    """Окно поочерёдной настройки фото на каждом бейдже."""

    finished = QtCore.Signal()
    back_to_menu = QtCore.Signal()

    def __init__(self, urls: List[str], template: BadgeTemplate):
        super(Constructor, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.badges: List[Badge] = []
        self.curr_badge_id = 0
        self._history: List[Tuple] = []
        self._errors: List[Tuple[str, str]] = []
        self._ready = False

        self._build_extra_fields(template)

        if not self.init_badges(urls, template):
            return

        self._ready = True
        self._connect()
        self.show_badge(0)

    # ------------------------------------------------------------------ #
    def is_ready(self) -> bool:
        return self._ready

    def _build_extra_fields(self, template: BadgeTemplate) -> None:
        """Создаёт поля ввода для произвольных текстовых полей из конфига."""
        self._extra_edits = {}
        for field in template.text_fields:
            if field.id in ("name", "surname"):
                continue
            edit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(field.label)
            self.ui.extra_fields_form.addRow(f"{field.label}:", edit)
            self._extra_edits[field.id] = edit
        if self._extra_edits:
            self.ui.extra_fields_box.show()

    # ------------------------------------------------------------------ #
    # Генерация бейджей
    # ------------------------------------------------------------------ #
    def init_badges(self, urls: List[str], template: BadgeTemplate) -> bool:
        """Создаёт все бейджи с прогресс-баром. Возвращает False при отмене/ошибке."""
        progress = QtWidgets.QProgressDialog(
            "Генерация бейджей…\n(детекция лиц и подготовка фото)", "Отмена", 0, len(urls), self)
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        for i, url in enumerate(urls):
            if progress.wasCanceled():
                progress.close()
                QtWidgets.QMessageBox.information(self, "Отменено", "Генерация отменена.")
                return False
            try:
                self.badges.append(Badge(i, url, template))
            except Exception as e:  # noqa: BLE001 — битое фото не должно ронять приложение
                self._errors.append((url, str(e)))
            progress.setValue(i + 1)
            QtWidgets.QApplication.processEvents()
        progress.close()

        if self._errors:
            summary = "\n".join(f"• {os.path.basename(url)}: {err}" for url, err in self._errors[:5])
            more = f"\n…и ещё {len(self._errors) - 5}" if len(self._errors) > 5 else ""
            QtWidgets.QMessageBox.warning(
                self, "Не удалось обработать",
                f"Пропущено файлов: {len(self._errors)}.\n{summary}{more}")
        if not self.badges:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Не удалось создать ни одного бейджа.")
            return False
        return True

    # ------------------------------------------------------------------ #
    # Навигация и превью
    # ------------------------------------------------------------------ #
    def _connect(self) -> None:
        ui = self.ui
        ui.btn_up.clicked.connect(lambda: self._translate(0, 5))
        ui.btn_down.clicked.connect(lambda: self._translate(0, -5))
        ui.btn_left.clicked.connect(lambda: self._translate(5, 0))
        ui.btn_right.clicked.connect(lambda: self._translate(-5, 0))
        ui.btn_zoom_in.clicked.connect(lambda: self._zoom(1.05))
        ui.btn_zoom_out.clicked.connect(lambda: self._zoom(0.95238095))
        ui.btn_undo.clicked.connect(self.undo)
        shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        shortcut.activated.connect(self.undo)
        ui.btn_apply_name.clicked.connect(self.apply_names)
        ui.edit_name.editingFinished.connect(self.apply_names)
        ui.edit_surname.editingFinished.connect(self.apply_names)
        for field_id, edit in self._extra_edits.items():
            edit.editingFinished.connect(
                lambda fid=field_id, e=edit: self._apply_extra(fid, e.text()))
        ui.btn_next.clicked.connect(self.next_badge)
        ui.btn_back.clicked.connect(self.prev_badge)
        ui.btn_finish.clicked.connect(self.finished.emit)
        ui.btn_to_menu.clicked.connect(self.request_back_to_menu)
        ui.preview_label.translated.connect(self._on_drag)
        ui.preview_label.zoomed.connect(self._zoom)

    @property
    def badge(self) -> Badge:
        return self.badges[self.curr_badge_id]

    def show_badge(self, index: int) -> None:
        self.curr_badge_id = index
        badge = self.badge
        self._history = []
        self.ui.label_counter.setText(f"Бейдж {index + 1} из {len(self.badges)}")
        self.ui.label_names.setText(f"{badge.get_surname()} {badge.get_name()}")
        self.ui.edit_surname.setText(badge.get_surname())
        self.ui.edit_name.setText(badge.get_name())
        for field_id, edit in self._extra_edits.items():
            edit.setText(badge.get_position() if field_id == "position" else "")
        self.ui.btn_back.setEnabled(index > 0)
        self.ui.btn_next.setEnabled(index < len(self.badges) - 1)
        self.update_preview()

    def update_preview(self) -> None:
        badge = self.badge
        image = badge.get_preview_image((720, 480))
        pixmap = pil_to_pixmap(image)
        # масштаб: сколько пикселей бейджа приходится на 1 px превью
        badge_w = badge.get_photo().size[0]
        self.ui.preview_label.set_scale(pixmap.width() / badge_w if badge_w else 1.0)
        self.ui.preview_label.setPixmap(pixmap)

    # ------------------------------------------------------------------ #
    # Правки
    # ------------------------------------------------------------------ #
    def _push_history(self) -> None:
        self._history.append(self.badge.get_photo_state())
        if len(self._history) > HISTORY_LIMIT:
            self._history.pop(0)

    def _translate(self, dx: int, dy: int) -> None:
        try:
            self._push_history()
            self.badge.translate_photo(dx, dy)
            if self.ui.check_apply_all.isChecked():
                for b in self.badges:
                    if b is not self.badge:
                        b.translate_photo(dx, dy)
            self.update_preview()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "Ошибка перемещения",
                f"Не удалось сдвинуть фото:\n{e}\n\nПодробности в консоли.")

    def _zoom(self, factor: float) -> None:
        try:
            self._push_history()
            self.badge.scale_photo(factor)
            if self.ui.check_apply_all.isChecked():
                for b in self.badges:
                    if b is not self.badge:
                        b.scale_photo(factor)
            self.update_preview()
        except Exception as e:  # noqa: BLE001 — показываем ошибку, а не «молчим»
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "Ошибка масштабирования",
                f"Не удалось изменить масштаб:\n{e}\n\nПодробности в консоли.")

    def _on_drag(self, dx: int, dy: int) -> None:
        """Перетаскивание мышью: содержимое двигается за курсором."""
        self._push_history()
        self.badge.translate_photo(-dx, -dy)
        if self.ui.check_apply_all.isChecked():
            for b in self.badges:
                if b is not self.badge:
                    b.translate_photo(-dx, -dy)
        self.update_preview()

    def undo(self) -> None:
        if not self._history:
            return
        state = self._history.pop()
        self.badge.set_photo_state(state)
        self.ui.edit_surname.setText(self.badge.get_surname())
        self.ui.edit_name.setText(self.badge.get_name())
        self.update_preview()

    def apply_names(self) -> None:
        name = self.ui.edit_name.text().strip()
        surname = self.ui.edit_surname.text().strip()
        self.badge.set_name(name)
        self.badge.set_surname(surname)
        if self.ui.check_apply_all.isChecked():
            for b in self.badges:
                if b is not self.badge:
                    b.set_name(name)
                    b.set_surname(surname)
        self.ui.label_names.setText(f"{surname} {name}")
        self.update_preview()

    def _apply_extra(self, field_id: str, value: str) -> None:
        self.badge.set_extra(field_id, value)
        if self.ui.check_apply_all.isChecked():
            for b in self.badges:
                if b is not self.badge:
                    b.set_extra(field_id, value)
        self.update_preview()

    def next_badge(self) -> None:
        if self.curr_badge_id < len(self.badges) - 1:
            self.show_badge(self.curr_badge_id + 1)

    def prev_badge(self) -> None:
        if self.curr_badge_id > 0:
            self.show_badge(self.curr_badge_id - 1)

    def request_back_to_menu(self) -> None:
        """Возврат в главное меню (правки бейджей будут перегенерированы)."""
        answer = QtWidgets.QMessageBox.question(
            self, "Вернуться в меню",
            "Текущие правки бейджей будут потеряны (генерация запустится "
            "заново). Вернуться в главное меню?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No)
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.back_to_menu.emit()
