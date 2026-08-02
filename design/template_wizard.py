"""Мастер настройки шаблона бейджа.

Позволяет без правки кода и JSON вручную расставить текстовые поля и область
фото на макете, задать размер бейджа в мм и сохранить всё в JSON-конфиг.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw
from PySide6 import QtCore, QtGui, QtWidgets

from badge_generator.template import BadgeTemplate, TextFieldConfig, TemplateConfigError
from design.pixmap_utils import pil_to_pixmap

FIELD_COLORS = [(230, 60, 60), (60, 120, 230), (60, 170, 90), (230, 150, 40), (160, 70, 200)]
PHOTO_COLOR = (0, 140, 255)
PREVIEW_MAX_W = 760
PREVIEW_MAX_H = 600
CORNER_HANDLE_SIZE = 16  # px на превью


class _PreviewLabel(QtWidgets.QLabel):
    """Метка с мышью: клик/перетаскивание по превью макета."""

    moved = QtCore.Signal(int, int)      # сдвиг в координатах макета
    clicked_at = QtCore.Signal(int, int)  # клик в координатах макета

    def __init__(self, scale: float = 1.0):
        super().__init__()
        self._scale = scale
        self._last: Optional[QtCore.QPoint] = None
        self.setMouseTracking(True)
        self.setMinimumSize(PREVIEW_MAX_W, PREVIEW_MAX_H)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

    def set_scale(self, scale: float) -> None:
        self._scale = scale

    def _to_template(self, pos: QtCore.QPoint) -> Tuple[int, int]:
        return int(pos.x() / self._scale), int(pos.y() / self._scale)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._last = event.pos()
            tx, ty = self._to_template(event.pos())
            self.clicked_at.emit(tx, ty)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._last is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self._last.x()
            dy = event.pos().y() - self._last.y()
            self._last = event.pos()
            if dx or dy:
                self.moved.emit(round(dx / self._scale), round(dy / self._scale))

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._last = None


class TemplateWizard(QtWidgets.QDialog):
    """Диалог настройки конфигурации шаблона (JSON рядом с макетом)."""

    def __init__(self, template_path: Path, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Настройка шаблона бейджа")
        self.resize(1180, 760)
        self._template_path = Path(template_path)

        # Загружаем существующий конфиг или создаём настройки по умолчанию
        config_loaded = True
        try:
            self.template = BadgeTemplate.from_template_file(self._template_path)
        except TemplateConfigError:
            self.template = BadgeTemplate(self._template_path,
                                          BadgeTemplate.default_config(self._template_path))
            config_loaded = False

        self._mode = "photo"  # id текстового поля или 'photo'
        self._drag: Optional[Tuple[str, int, int]] = None  # (тип, смещение x, смещение y)

        self._build_ui()
        self._sync_controls_from_template()
        self._update_preview()
        if not config_loaded:
            QtWidgets.QMessageBox.information(
                self, "Новый конфиг",
                "Конфиг для этого макета не найден — созданы настройки по умолчанию.\n\n"
                "Как настроить:\n"
                "• над макетом выберите элемент (текст «Имя» / «Фамилия» / «Фото область»);\n"
                "• кликните по макету — элемент встанет в точку клика;\n"
                "• перетаскивайте его мышью; у области фото тяните синий уголок;\n"
                "• справа задайте размер шрифта, размер бейджа в мм и др.;\n"
                "• нажмите «Сохранить конфиг».")

    # ------------------------------------------------------------------ #
    # Построение интерфейса
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # --- левая часть: превью --------------------------------------- #
        left = QtWidgets.QVBoxLayout()

        header = QtWidgets.QHBoxLayout()
        self.hint_label = QtWidgets.QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            "background: #e8f0fe; color: #1e3a8a; border: 1px solid #bfdbfe;"
            "border-radius: 8px; padding: 8px 12px; font-weight: 600;")
        header.addWidget(self.hint_label, stretch=1)
        self.btn_help = QtWidgets.QPushButton("?")
        self.btn_help.setFixedSize(32, 32)
        self.btn_help.setToolTip("Подробная инструкция")
        header.addWidget(self.btn_help)
        left.addLayout(header)

        self.preview_label = _PreviewLabel()
        self.preview_label.clicked_at.connect(self._on_preview_click)
        self.preview_label.moved.connect(self._on_preview_move)
        left.addWidget(self.preview_label)

        self.mode_combo = QtWidgets.QComboBox()
        left.addWidget(self.mode_combo)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addLayout(left, stretch=3)

        # --- правая часть: панель настроек ------------------------------ #
        right = QtWidgets.QVBoxLayout()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QtWidgets.QWidget()
        form = QtWidgets.QVBoxLayout(panel)
        form.setContentsMargins(8, 8, 8, 8)

        # размер бейджа
        size_box = QtWidgets.QGroupBox("Размер бейджа (для печати)")
        size_form = QtWidgets.QFormLayout(size_box)
        self.spin_badge_w = QtWidgets.QSpinBox()
        self.spin_badge_w.setRange(20, 500)
        self.spin_badge_w.setSuffix(" мм")
        self.spin_badge_h = QtWidgets.QSpinBox()
        self.spin_badge_h.setRange(20, 500)
        self.spin_badge_h.setSuffix(" мм")
        self.spin_dpi = QtWidgets.QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        self.spin_dpi.setSuffix(" dpi")
        size_form.addRow("Ширина:", self.spin_badge_w)
        size_form.addRow("Высота:", self.spin_badge_h)
        size_form.addRow("Разрешение:", self.spin_dpi)
        form.addWidget(size_box)

        # текстовые поля
        fields_box = QtWidgets.QGroupBox("Текстовые поля")
        fields_v = QtWidgets.QVBoxLayout(fields_box)
        self.fields_list = QtWidgets.QListWidget()
        self.fields_list.setMaximumHeight(110)
        fields_v.addWidget(self.fields_list)
        fields_btns = QtWidgets.QHBoxLayout()
        self.btn_add_field = QtWidgets.QPushButton("+ поле")
        self.btn_remove_field = QtWidgets.QPushButton("− поле")
        fields_btns.addWidget(self.btn_add_field)
        fields_btns.addWidget(self.btn_remove_field)
        fields_v.addLayout(fields_btns)
        field_form = QtWidgets.QFormLayout()
        self.edit_label = QtWidgets.QLineEdit()
        self.spin_font_size = QtWidgets.QSpinBox()
        self.spin_font_size.setRange(8, 2000)
        self.spin_max_width = QtWidgets.QSpinBox()
        self.spin_max_width.setRange(0, 20000)
        self.spin_max_width.setSuffix(" px (0 = без ограничения)")
        self.check_auto_shrink = QtWidgets.QCheckBox("уменьшать шрифт, если не влезает")
        self.check_uppercase = QtWidgets.QCheckBox("заглавными буквами")
        self.combo_align = QtWidgets.QComboBox()
        self.combo_align.addItems(["left", "center", "right"])
        self.btn_color = QtWidgets.QPushButton()
        self.btn_color.setFixedWidth(90)
        self.spin_anchor_x = QtWidgets.QSpinBox()
        self.spin_anchor_x.setRange(0, 20000)
        self.spin_anchor_y = QtWidgets.QSpinBox()
        self.spin_anchor_y.setRange(0, 20000)
        field_form.addRow("Подпись:", self.edit_label)
        field_form.addRow("Размер шрифта:", self.spin_font_size)
        field_form.addRow("Макс. ширина:", self.spin_max_width)
        field_form.addRow("", self.check_auto_shrink)
        field_form.addRow("", self.check_uppercase)
        field_form.addRow("Выравнивание:", self.combo_align)
        field_form.addRow("Цвет:", self.btn_color)
        field_form.addRow("Якорь X:", self.spin_anchor_x)
        field_form.addRow("Якорь Y:", self.spin_anchor_y)
        fields_v.addLayout(field_form)
        form.addWidget(fields_box)

        # фото
        photo_box = QtWidgets.QGroupBox("Область фото")
        photo_form = QtWidgets.QFormLayout(photo_box)
        self.spin_photo_x = QtWidgets.QSpinBox()
        self.spin_photo_x.setRange(0, 20000)
        self.spin_photo_y = QtWidgets.QSpinBox()
        self.spin_photo_y.setRange(0, 20000)
        self.spin_photo_w = QtWidgets.QSpinBox()
        self.spin_photo_w.setRange(1, 20000)
        self.spin_photo_h = QtWidgets.QSpinBox()
        self.spin_photo_h.setRange(1, 20000)
        self.spin_crop_w = QtWidgets.QSpinBox()
        self.spin_crop_w.setRange(1, 20000)
        self.spin_crop_h = QtWidgets.QSpinBox()
        self.spin_crop_h.setRange(1, 20000)
        self.spin_face_scale = QtWidgets.QDoubleSpinBox()
        self.spin_face_scale.setRange(0.05, 5.0)
        self.spin_face_scale.setSingleStep(0.05)
        self.spin_face_offset = QtWidgets.QDoubleSpinBox()
        self.spin_face_offset.setRange(0.5, 3.0)
        self.spin_face_offset.setSingleStep(0.05)
        self.check_remove_bg = QtWidgets.QCheckBox("удалять светлый фон с фото")
        photo_form.addRow("Позиция X:", self.spin_photo_x)
        photo_form.addRow("Позиция Y:", self.spin_photo_y)
        photo_form.addRow("Ширина:", self.spin_photo_w)
        photo_form.addRow("Высота:", self.spin_photo_h)
        photo_form.addRow("Кадр из фото W:", self.spin_crop_w)
        photo_form.addRow("Кадр из фото H:", self.spin_crop_h)
        photo_form.addRow("Масштаб по лицу:", self.spin_face_scale)
        photo_form.addRow("Смещение лица по Y:", self.spin_face_offset)
        photo_form.addRow("", self.check_remove_bg)
        form.addWidget(photo_box)

        form.addStretch(1)
        scroll.setWidget(panel)
        right.addWidget(scroll, stretch=1)

        # кнопки
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_save = QtWidgets.QPushButton("Сохранить конфиг")
        self.btn_save.setDefault(True)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        right.addLayout(buttons)
        layout.addLayout(right, stretch=2)

        # --- соединения ------------------------------------------------ #
        self.fields_list.currentRowChanged.connect(self._on_field_selected)
        self.btn_add_field.clicked.connect(self._add_field)
        self.btn_remove_field.clicked.connect(self._remove_field)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._save)
        self.btn_help.clicked.connect(self._show_help)

        self._update_hint()

        for spin in (self.spin_badge_w, self.spin_badge_h, self.spin_dpi):
            spin.valueChanged.connect(self._on_size_changed)
        for spin in (self.spin_photo_x, self.spin_photo_y, self.spin_photo_w, self.spin_photo_h,
                     self.spin_crop_w, self.spin_crop_h):
            spin.valueChanged.connect(self._on_photo_spin_changed)
        self.spin_face_scale.valueChanged.connect(self._on_photo_spin_changed)
        self.spin_face_offset.valueChanged.connect(self._on_photo_spin_changed)
        self.check_remove_bg.toggled.connect(self._on_photo_spin_changed)
        for w in (self.edit_label, self.spin_font_size, self.spin_max_width,
                  self.combo_align, self.spin_anchor_x, self.spin_anchor_y):
            if isinstance(w, QtWidgets.QLineEdit):
                w.textChanged.connect(self._on_field_spin_changed)
            elif isinstance(w, QtWidgets.QComboBox):
                w.currentIndexChanged.connect(self._on_field_spin_changed)
            else:
                w.valueChanged.connect(self._on_field_spin_changed)
        self.check_auto_shrink.toggled.connect(self._on_field_spin_changed)
        self.check_uppercase.toggled.connect(self._on_field_spin_changed)
        self.btn_color.clicked.connect(self._pick_color)

    # ------------------------------------------------------------------ #
    # Синхронизация «контролы <-> шаблон»
    # ------------------------------------------------------------------ #
    def _rebuild_mode_combo(self) -> None:
        current = self._mode
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        for f in self.template.text_fields:
            self.mode_combo.addItem(f"Текст: {f.label}", ("field", f.id))
        self.mode_combo.addItem("Фото область", ("photo", None))
        # восстановить выбор
        for i in range(self.mode_combo.count()):
            kind, value = self.mode_combo.itemData(i)
            if (kind == "field" and current == value) or (kind == "photo" and current == "photo"):
                self.mode_combo.setCurrentIndex(i)
                break
        self.mode_combo.blockSignals(False)

    def _rebuild_fields_list(self) -> None:
        current_id = None
        row = self.fields_list.currentRow()
        if 0 <= row < len(self.template.text_fields):
            current_id = self.template.text_fields[row].id
        self.fields_list.blockSignals(True)
        self.fields_list.clear()
        for f in self.template.text_fields:
            self.fields_list.addItem(f"{f.label} ({f.id})")
        if current_id is not None:
            for i, f in enumerate(self.template.text_fields):
                if f.id == current_id:
                    self.fields_list.setCurrentRow(i)
                    break
        elif self.template.text_fields:
            self.fields_list.setCurrentRow(0)
        self.fields_list.blockSignals(False)

    def _sync_controls_from_template(self) -> None:
        t = self.template
        self.spin_badge_w.setValue(t.badge_size_mm[0])
        self.spin_badge_h.setValue(t.badge_size_mm[1])
        self.spin_dpi.setValue(t.dpi)
        self.spin_photo_x.setValue(t.photo.place_on_badge[0])
        self.spin_photo_y.setValue(t.photo.place_on_badge[1])
        self.spin_photo_w.setValue(t.photo.place_on_badge[2])
        self.spin_photo_h.setValue(t.photo.place_on_badge[3])
        self.spin_crop_w.setValue(t.photo.crop_size[0])
        self.spin_crop_h.setValue(t.photo.crop_size[1])
        self.spin_face_scale.setValue(t.photo.face_scale)
        self.spin_face_offset.setValue(t.photo.face_offset_y)
        self.check_remove_bg.setChecked(t.photo.remove_background)
        self._rebuild_fields_list()
        self._rebuild_mode_combo()
        self._sync_field_controls()

    def _current_field(self) -> Optional[TextFieldConfig]:
        if self._mode == "photo":
            return None
        return self.template.get_text_field(self._mode)

    def _sync_field_controls(self) -> None:
        field = self._current_field()
        enabled = field is not None
        for w in (self.edit_label, self.spin_font_size, self.spin_max_width, self.combo_align,
                  self.spin_anchor_x, self.spin_anchor_y, self.btn_color,
                  self.check_auto_shrink, self.check_uppercase):
            w.setEnabled(enabled)
        if field is None:
            return
        self.edit_label.setText(field.label)
        self.spin_font_size.setValue(field.font_size)
        self.spin_max_width.setValue(field.max_width)
        self.combo_align.setCurrentText(field.align)
        self.spin_anchor_x.setValue(field.anchor[0])
        self.spin_anchor_y.setValue(field.anchor[1])
        self.check_auto_shrink.setChecked(field.auto_shrink)
        self.check_uppercase.setChecked(field.uppercase)
        color = QtGui.QColor(*field.color[:3])
        self.btn_color.setStyleSheet(f"background-color: {color.name()};")
        self.btn_color.setText(color.name())

    # ------------------------------------------------------------------ #
    # Обработчики
    # ------------------------------------------------------------------ #
    def _on_mode_changed(self, index: int) -> None:
        if index < 0:
            return
        kind, value = self.mode_combo.itemData(index)
        self._mode = value if kind == "field" else "photo"
        self._sync_field_controls()
        self._update_hint()

    def _update_hint(self) -> None:
        """Подсказка над превью: что делать в текущем режиме."""
        if self._mode == "photo":
            self.hint_label.setText(
                "Область фото: кликните по макету — левый верхний угол фото "
                "встанет в точку клика. Затем тяните за синий уголок вниз-вправо, "
                "чтобы растянуть область, или перетаскивайте область целиком.")
        else:
            field = self._current_field()
            if field is not None:
                self.hint_label.setText(
                    f"Текстовое поле «{field.label}»: кликните по макету — "
                    "текст будет начинаться в точке клика. Затем перетаскивайте "
                    "поле мышью, чтобы подвинуть его. Размер шрифта настраивается "
                    "справа в блоке «Текстовые поля».")

    def _show_help(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Как настроить шаблон",
            "1. Сверху над макетом выберите, что настраиваете: текстовое поле "
            "(«Имя», «Фамилия») или «Фото область».\n"
            "2. Кликните по макету — выбранный элемент встанет в точку клика "
            "(для текста — его начало, для фото — левый верхний угол).\n"
            "3. Перетаскивайте элемент мышью, чтобы двигать его. У области фото "
            "есть синий уголок в правом нижнем углу — тяните его, чтобы менять "
            "размер области.\n"
            "4. Параметры выбранного элемента меняются в панели справа: "
            "размер шрифта, выравнивание, цвет, «уменьшать шрифт, если не "
            "влезает» — для текста; для фото — масштаб по лицу и др.\n"
            "5. Укажите физический размер бейджа в миллиметрах (измерьте "
            "линейкой ваш бейдж) — от него зависит раскладка в PDF.\n"
            "6. Нажмите «Сохранить конфиг» — рядом с макетом появится "
            "JSON-файл, и макет станет готов к использованию.\n\n"
            "Подсказка: если у вас уже есть готовый бейдж (пример результата), "
            "можно не расставлять ничего вручную — утилита "
            "tools/derive_config.py сама определит координаты текста и фото "
            "по сравнению макета и готового бейджа.")

    def _on_field_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.template.text_fields):
            return
        field = self.template.text_fields[row]
        self._mode = field.id
        self._rebuild_mode_combo()
        self._sync_field_controls()
        self._update_preview()

    def _add_field(self) -> None:
        base = f"field{len(self.template.text_fields) + 1}"
        field = TextFieldConfig({
            "id": base, "label": base,
            "anchor": [int(self.template.size[0] * 0.2), int(self.template.size[1] * 0.5)],
            "font": "assets/Montserrat.ttf", "font_size": 100,
            "max_width": 0, "auto_shrink": False, "uppercase": False,
        }, self.template.config_dir)
        self.template.text_fields.append(field)
        self._rebuild_fields_list()
        self._rebuild_mode_combo()
        self.fields_list.setCurrentRow(len(self.template.text_fields) - 1)
        self._update_preview()

    def _remove_field(self) -> None:
        if len(self.template.text_fields) <= 1:
            QtWidgets.QMessageBox.warning(self, "Внимание", "Должно остаться хотя бы одно текстовое поле.")
            return
        field = self._current_field()
        if field is None:
            return
        self.template.text_fields = [f for f in self.template.text_fields if f.id != field.id]
        self._mode = self.template.text_fields[0].id
        self._rebuild_fields_list()
        self._rebuild_mode_combo()
        self._sync_field_controls()
        self._update_preview()

    def _pick_color(self) -> None:
        field = self._current_field()
        if field is None:
            return
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*field.color[:3]), self, "Цвет текста")
        if color.isValid():
            field.color = (color.red(), color.green(), color.blue(), 255)
            self._sync_field_controls()
            self._update_preview()

    def _on_size_changed(self) -> None:
        self.template.badge_size_mm = (self.spin_badge_w.value(), self.spin_badge_h.value())
        self.template.dpi = self.spin_dpi.value()

    def _on_field_spin_changed(self) -> None:
        field = self._current_field()
        if field is None:
            return
        field.label = self.edit_label.text().strip() or field.id
        field.font_size = self.spin_font_size.value()
        field.max_width = self.spin_max_width.value()
        field.align = self.combo_align.currentText()
        field.anchor = (self.spin_anchor_x.value(), self.spin_anchor_y.value())
        field.auto_shrink = self.check_auto_shrink.isChecked()
        field.uppercase = self.check_uppercase.isChecked()
        item = self.fields_list.currentItem()
        if item is not None:
            item.setText(f"{field.label} ({field.id})")
        self._update_preview()

    def _on_photo_spin_changed(self) -> None:
        self.template.photo.place_on_badge = (
            self.spin_photo_x.value(), self.spin_photo_y.value(),
            self.spin_photo_w.value(), self.spin_photo_h.value())
        self.template.photo.crop_size = (self.spin_crop_w.value(), self.spin_crop_h.value())
        self.template.photo.face_scale = self.spin_face_scale.value()
        self.template.photo.face_offset_y = self.spin_face_offset.value()
        self.template.photo.remove_background = self.check_remove_bg.isChecked()
        self._update_preview()

    # ------------------------------------------------------------------ #
    # Работа с превью
    # ------------------------------------------------------------------ #
    def _preview_scale(self) -> float:
        tw, th = self.template.size
        return min(PREVIEW_MAX_W / tw, PREVIEW_MAX_H / th, 1.0)

    def _update_preview(self) -> None:
        img = self.template.image.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i, f in enumerate(self.template.text_fields):
            color = FIELD_COLORS[i % len(FIELD_COLORS)]
            box_w = f.max_width or int(img.width * 0.3)
            box_h = max(20, int(f.font_size * 1.2))
            box = (f.anchor[0], f.anchor[1], f.anchor[0] + box_w, f.anchor[1] + box_h)
            od.rectangle(box, outline=color + (255,), width=3)
            od.text((f.anchor[0] + 4, f.anchor[1] - box_h // 3), f.label,
                    fill=color + (255,))
        x, y, w, h = self.template.photo.place_on_badge
        od.rectangle((x, y, x + w, y + h), outline=PHOTO_COLOR + (255,), width=4)
        od.rectangle((x + w - CORNER_HANDLE_SIZE, y + h - CORNER_HANDLE_SIZE,
                      x + w, y + h), fill=PHOTO_COLOR + (255,))
        preview = Image.alpha_composite(img, overlay)

        scale = self._preview_scale()
        if scale < 1.0:
            preview = preview.resize((max(1, round(preview.width * scale)),
                                      max(1, round(preview.height * scale))),
                                     Image.Resampling.LANCZOS)
        self.preview_label.set_scale(scale)
        self.preview_label.setPixmap(pil_to_pixmap(preview))

    def _on_preview_click(self, tx: int, ty: int) -> None:
        tw, th = self.template.size
        tx = min(max(0, tx), tw)
        ty = min(max(0, ty), th)
        if self._mode == "photo":
            x, y, w, h = self.template.photo.place_on_badge
            # клик по правому нижнему углу — начало изменения размера
            if abs(tx - (x + w)) < CORNER_HANDLE_SIZE and abs(ty - (y + h)) < CORNER_HANDLE_SIZE:
                self._drag = ("photo_resize", 0, 0)
            else:
                self.template.photo.place_on_badge = (tx, ty, w, h)
                self._drag = ("photo_move", 0, 0)  # элемент уже у курсора
            self._sync_photo_spins()
        else:
            field = self._current_field()
            if field is not None:
                field.anchor = (tx, ty)
                self._drag = ("field_move", 0, 0)  # элемент уже у курсора
                self._sync_field_controls()
        self._update_preview()

    def _on_preview_move(self, dx: int, dy: int) -> None:
        if self._drag is None:
            return
        kind, off_x, off_y = self._drag
        tw, th = self.template.size
        if kind == "photo_move":
            x, y, w, h = self.template.photo.place_on_badge
            nx = min(max(0, x + dx), tw - 1)
            ny = min(max(0, y + dy), th - 1)
            self.template.photo.place_on_badge = (nx, ny, w, h)
            self._sync_photo_spins()
        elif kind == "photo_resize":
            x, y, w, h = self.template.photo.place_on_badge
            nw = min(max(1, w + dx), tw - x)
            nh = min(max(1, h + dy), th - y)
            self.template.photo.place_on_badge = (x, y, nw, nh)
            self._sync_photo_spins()
        elif kind == "field_move":
            field = self._current_field()
            if field is not None:
                ax, ay = field.anchor
                field.anchor = (min(max(0, ax + dx), tw), min(max(0, ay + dy), th))
                self._sync_field_controls()
        self._update_preview()

    def _sync_photo_spins(self) -> None:
        x, y, w, h = self.template.photo.place_on_badge
        for spin, value in ((self.spin_photo_x, x), (self.spin_photo_y, y),
                            (self.spin_photo_w, w), (self.spin_photo_h, h)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    # ------------------------------------------------------------------ #
    # Сохранение
    # ------------------------------------------------------------------ #
    def _save(self) -> None:
        try:
            path = self.template.save_json()
        except Exception as e:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить конфиг:\n{e}")
            return
        QtWidgets.QMessageBox.information(
            self, "Готово",
            f"Конфигурация сохранена:\n{path}\n\nТеперь этот макет можно использовать.")
        self.accept()
