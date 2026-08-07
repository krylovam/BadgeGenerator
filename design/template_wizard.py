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


def preview_to_template(px: float, py: float, origin_x: float, origin_y: float,
                        scale: float) -> Tuple[int, int]:
    """Координаты клика (px, py) в пикселях превью -> координаты макета.

    origin_x/origin_y — смещение pixmap внутри QLabel (превью центрируется).
    """
    return int((px - origin_x) / scale), int((py - origin_y) / scale)


class _PreviewLabel(QtWidgets.QLabel):
    """Метка с мышью: клик/перетаскивание по превью макета."""

    moved = QtCore.Signal(int, int)      # сдвиг в координатах макета
    clicked_at = QtCore.Signal(int, int)  # клик в координатах макета
    released = QtCore.Signal()            # отпускание левой кнопки мыши

    def __init__(self, scale: float = 1.0):
        super().__init__()
        self._scale = scale
        self._last: Optional[QtCore.QPoint] = None
        self._origin_x = 0
        self._origin_y = 0
        self.setMouseTracking(True)
        self.setMinimumSize(PREVIEW_MAX_W, PREVIEW_MAX_H)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

    def set_scale(self, scale: float) -> None:
        self._scale = scale

    def setPixmap(self, pixmap: QtGui.QPixmap) -> None:  # noqa: N802 — переопределение Qt
        super().setPixmap(pixmap)
        self._update_origin()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_origin()

    def _update_origin(self) -> None:
        """Pixmap центрируется в метке — запоминаем её смещение."""
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            self._origin_x = self._origin_y = 0
            return
        self._origin_x = max(0, (self.width() - pixmap.width()) // 2)
        self._origin_y = max(0, (self.height() - pixmap.height()) // 2)

    def _to_template(self, pos: QtCore.QPoint) -> Tuple[int, int]:
        return preview_to_template(pos.x(), pos.y(),
                                   self._origin_x, self._origin_y, self._scale)

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
        self.released.emit()


class TemplateWizard(QtWidgets.QDialog):
    """Диалог настройки конфигурации шаблона (JSON рядом с макетом)."""

    def __init__(self, template_path: Path, photos=None, template=None,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Настройка шаблона бейджа")
        self.resize(1180, 760)
        self._template_path = Path(template_path)
        self._photos = list(photos or [])
        self._example_photo: Optional[str] = None
        self._example_badge = None
        self._photo_params_dirty = False
        self._preview_scale = 1.0

        # Загружаем существующий конфиг или создаём настройки по умолчанию.
        # Если передан template (из главного меню — с уже применёнными
        # изменениями типа «Педсостав»), используем его, иначе читаем из файла.
        config_loaded = True
        if template is not None:
            self.template = template
        else:
            try:
                self.template = BadgeTemplate.from_template_file(self._template_path)
            except TemplateConfigError:
                self.template = BadgeTemplate(self._template_path,
                                              BadgeTemplate.default_config(self._template_path))
                config_loaded = False

        self._mode = "photo"  # id текстового поля или 'photo'
        self._drag: Optional[str] = None  # 'photo_move' / 'photo_resize' / 'field_move'

        self._build_ui()
        self._sync_controls_from_template()
        self._fill_example_photo_combo()
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

        # --- левая часть: вкладки «Расстановка» / «Пример бейджа» ------- #
        left = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()
        left.addWidget(self.tabs)

        # вкладка 1: расстановка элементов
        tab_place = QtWidgets.QWidget()
        tab_place_layout = QtWidgets.QVBoxLayout(tab_place)
        tab_place_layout.setContentsMargins(4, 8, 4, 4)

        header = QtWidgets.QHBoxLayout()
        self.hint_label = QtWidgets.QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            "background: #e8f0fe; color: #1e3a8a; border: 1px solid #bfdbfe;"
            "border-radius: 8px; padding: 8px 12px; font-weight: 600;")
        header.addWidget(self.hint_label, stretch=1)
        self.btn_show_example = QtWidgets.QPushButton("Пример бейджа →")
        self.btn_show_example.setToolTip(
            "Показать готовый бейдж с реальным фото (вкладка «Пример бейджа»)")
        header.addWidget(self.btn_show_example)
        self.btn_help = QtWidgets.QPushButton("?")
        self.btn_help.setFixedSize(32, 32)
        self.btn_help.setToolTip("Подробная инструкция")
        header.addWidget(self.btn_help)
        tab_place_layout.addLayout(header)

        self.preview_label = _PreviewLabel()
        self.preview_label.clicked_at.connect(self._on_preview_click)
        self.preview_label.moved.connect(self._on_preview_move)
        self.preview_label.released.connect(self._on_preview_released)
        tab_place_layout.addWidget(self.preview_label)

        self.mode_combo = QtWidgets.QComboBox()
        tab_place_layout.addWidget(self.mode_combo)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # вкладка 2: пример итогового бейджа
        tab_example = QtWidgets.QWidget()
        tab_example_layout = QtWidgets.QVBoxLayout(tab_example)
        tab_example_layout.setContentsMargins(4, 8, 4, 4)

        example_row = QtWidgets.QHBoxLayout()
        example_row.addWidget(QtWidgets.QLabel("Фото для примера:"))
        self.combo_example_photo = QtWidgets.QComboBox()
        self.combo_example_photo.setMinimumWidth(240)
        example_row.addWidget(self.combo_example_photo, stretch=1)
        self.btn_pick_photo = QtWidgets.QPushButton("Выбрать фото…")
        example_row.addWidget(self.btn_pick_photo)
        tab_example_layout.addLayout(example_row)

        self.example_label = QtWidgets.QLabel("Выберите фото, чтобы увидеть пример бейджа")
        self.example_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.example_label.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.example_label.setMinimumSize(400, 300)
        tab_example_layout.addWidget(self.example_label, stretch=1)

        self.example_info = QtWidgets.QLabel("")
        self.example_info.setWordWrap(True)
        self.example_info.setStyleSheet("color: #555;")
        tab_example_layout.addWidget(self.example_info)

        self.tabs.addTab(tab_place, "Расстановка элементов")
        self.tabs.addTab(tab_example, "Пример бейджа")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.combo_example_photo.currentIndexChanged.connect(self._on_example_photo_changed)
        self.btn_pick_photo.clicked.connect(self._pick_example_photo)
        self.btn_show_example.clicked.connect(lambda: self.tabs.setCurrentIndex(1))

        layout.addLayout(left, stretch=3)

        # --- правая часть: панель настроек ------------------------------ #
        right = QtWidgets.QVBoxLayout()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QtWidgets.QWidget()
        form = QtWidgets.QVBoxLayout(panel)
        form.setContentsMargins(8, 8, 8, 8)

        # тип бейджа
        type_box = QtWidgets.QGroupBox("Тип бейджа (поля из имени файла)")
        type_form = QtWidgets.QVBoxLayout(type_box)
        self.radio_listener = QtWidgets.QRadioButton("Слушатель — 2 поля (имя, фамилия)")
        self.radio_staff = QtWidgets.QRadioButton("Педсостав — 3 поля (имя, фамилия, должность)")
        self.radio_listener.setChecked(True)
        type_form.addWidget(self.radio_listener)
        type_form.addWidget(self.radio_staff)
        form.addWidget(type_box)

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
        # кадр теперь автоматический: пропорции = пропорциям области на макете
        self.spin_crop_w.setEnabled(False)
        self.spin_crop_h.setEnabled(False)
        crop_auto_label = QtWidgets.QLabel(
            "Автоматически: фото вписывается в область с её пропорциями")
        crop_auto_label.setStyleSheet("color: #667; font-size: 11px;")
        crop_auto_label.setWordWrap(True)
        self.spin_face_scale = QtWidgets.QDoubleSpinBox()
        self.spin_face_scale.setRange(0.1, 2.0)
        self.spin_face_scale.setSingleStep(0.05)
        self.spin_face_offset = QtWidgets.QDoubleSpinBox()
        self.spin_face_offset.setRange(0.5, 3.0)
        self.spin_face_offset.setSingleStep(0.05)
        self.check_remove_bg = QtWidgets.QCheckBox("вырезать человека с фото (убрать фон)")
        self.combo_bg_mode = QtWidgets.QComboBox()
        self.combo_bg_mode.addItem("Нейросеть U²-Net — любой фон (рекомендуется)", "unet")
        self.combo_bg_mode.addItem("Вырезание человека (GrabCut)", "grabcut")
        self.combo_bg_mode.addItem("Светлый фон (по яркости)", "brightness")
        self.spin_bg_threshold = QtWidgets.QSpinBox()
        self.spin_bg_threshold.setRange(1, 254)
        self.spin_bg_threshold.setValue(200)
        self.spin_bg_threshold.setToolTip(
            "Пиксели ярче этого значения считаются фоном. Если фон не удаляется "
            "полностью — уменьшите значение (например 180).")
        face_scale_hint = QtWidgets.QLabel(
            "0.3 — по пояс · 0.4–0.5 — портрет (рекомендуется) · 0.7–1.0 — крупно, только лицо")
        face_scale_hint.setStyleSheet("color: #667; font-size: 11px;")
        face_scale_hint.setWordWrap(True)
        photo_form.addRow("Позиция X:", self.spin_photo_x)
        photo_form.addRow("Позиция Y:", self.spin_photo_y)
        photo_form.addRow("Ширина:", self.spin_photo_w)
        photo_form.addRow("Высота:", self.spin_photo_h)
        photo_form.addRow("Кадр из фото:", crop_auto_label)
        photo_form.addRow("Масштаб по лицу:", self.spin_face_scale)
        photo_form.addRow("", face_scale_hint)
        photo_form.addRow("Смещение лица по Y:", self.spin_face_offset)
        photo_form.addRow("", self.check_remove_bg)
        photo_form.addRow("Способ:", self.combo_bg_mode)
        photo_form.addRow("Порог фона (яркость):", self.spin_bg_threshold)
        form.addWidget(photo_box)

        form.addStretch(1)
        scroll.setWidget(panel)
        right.addWidget(scroll, stretch=1)

        # кнопки
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.btn_quick_config = QtWidgets.QPushButton("Быстрая настройка по готовому бейджу…")
        self.btn_quick_config.setToolTip(
            "Выберите готовый бейдж (пример результата) — координаты текста и "
            "фото определятся автоматически")
        buttons.addWidget(self.btn_quick_config)
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
        self.btn_quick_config.clicked.connect(self._quick_config_from_ready)

        self._update_hint()

        for spin in (self.spin_badge_w, self.spin_badge_h, self.spin_dpi):
            spin.valueChanged.connect(self._on_size_changed)
        for spin in (self.spin_photo_x, self.spin_photo_y, self.spin_photo_w, self.spin_photo_h,
                     self.spin_crop_w, self.spin_crop_h):
            spin.valueChanged.connect(self._on_photo_spin_changed)
        self.spin_face_scale.valueChanged.connect(self._on_photo_spin_changed)
        self.spin_face_offset.valueChanged.connect(self._on_photo_spin_changed)
        self.check_remove_bg.toggled.connect(self._on_photo_spin_changed)
        self.combo_bg_mode.currentIndexChanged.connect(self._on_photo_spin_changed)
        self.spin_bg_threshold.valueChanged.connect(self._on_photo_spin_changed)
        self.radio_listener.toggled.connect(self._on_name_format_changed)
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
        # Блокируем сигналы при установке значений: иначе каждый setValue
        # триггерит _on_photo_spin_changed, который видит «изменение области»
        # по промежуточным значениям и пересчитывает кадр и face_scale —
        # сохранённые настройки положения фото слетают.
        blocked = (self.spin_badge_w, self.spin_badge_h, self.spin_dpi,
                   self.spin_photo_x, self.spin_photo_y,
                   self.spin_photo_w, self.spin_photo_h,
                   self.spin_crop_w, self.spin_crop_h,
                   self.spin_face_scale, self.spin_face_offset,
                   self.spin_bg_threshold, self.check_remove_bg,
                   self.combo_bg_mode)
        for w in blocked:
            w.blockSignals(True)
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
        idx = self.combo_bg_mode.findData(t.photo.remove_bg_mode)
        self.combo_bg_mode.setCurrentIndex(max(0, idx))
        self.spin_bg_threshold.setValue(t.photo.remove_bg_threshold)
        for w in blocked:
            w.blockSignals(False)
        # тип бейджа
        self.radio_listener.blockSignals(True)
        self.radio_staff.blockSignals(True)
        self.radio_listener.setChecked(t.name_format != "staff")
        self.radio_staff.setChecked(t.name_format == "staff")
        self.radio_listener.blockSignals(False)
        self.radio_staff.blockSignals(False)
        self._rebuild_fields_list()
        self._rebuild_mode_combo()
        self._sync_field_controls()
        # НЕ подгоняем кадр при загрузке существующего конфига: сохранённые
        # crop_size/face_scale/place_on_badge остаются как есть. Подгонка
        # происходит только при интерактивном изменении области в мастере.
        # если тип «педсостав», а поля должности нет — добавить
        if self.template.name_format == "staff" and self.template.get_text_field("position") is None:
            self._on_name_format_changed()

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
                "встанет в точку клика. Кликните по самой области — и тяните "
                "её мышью, чтобы двигать. Синий уголок в правом нижнем углу "
                "растягивает область. Фото автоматически вписывается в область "
                "с её пропорциями — выберите лишь «Масштаб по лицу» в панели "
                "справа. Готовый бейдж смотрите на вкладке «Пример бейджа».")
        else:
            field = self._current_field()
            if field is not None:
                self.hint_label.setText(
                    f"Текстовое поле «{field.label}»: кликните по макету — "
                    "текст будет начинаться в точке клика. Кликните по полю и "
                    "тяните его мышью, чтобы двигать. Размер шрифта и другие "
                    "параметры — справа в блоке «Текстовые поля». Готовый бейдж "
                    "смотрите на вкладке «Пример бейджа».")

    def _show_help(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Как настроить шаблон",
            "1. На вкладке «Расстановка элементов» выберите, что настраиваете: "
            "текстовое поле («Имя», «Фамилия») или «Фото область».\n"
            "2. Кликните по макету — выбранный элемент встанет в точку клика "
            "(для текста — его начало, для фото — левый верхний угол).\n"
            "3. Чтобы двигать элемент — кликните по нему и перетаскивайте "
            "мышью (элемент «схватится» за точку клика, без скачков). У области "
            "фото есть синий уголок в правом нижнем углу — тяните его, чтобы "
            "менять размер области.\n"
            "4. Параметры выбранного элемента меняются в панели справа: "
            "размер шрифта, выравнивание, цвет, «уменьшать шрифт, если не "
            "влезает» — для текста; для фото — масштаб по лицу и др.\n"
            "5. На вкладке «Пример бейджа» сразу видно, как будет выглядеть "
            "бейдж с реальным фото и подписями — выберите фото участника "
            "из загруженной папки или любое другое.\n"
            "6. Укажите физический размер бейджа в миллиметрах (измерьте "
            "линейкой ваш бейдж) — от него зависит раскладка в PDF.\n"
            "7. Нажмите «Сохранить конфиг» — рядом с макетом появится "
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
        """Ручное изменение параметров фото в панели справа.

        Область на макете (позиция/размер) задаётся пользователем, кадр
        (crop W/H) подгоняется автоматически под пропорции области.
        """
        old_place = self.template.photo.place_on_badge
        new_place = (self.spin_photo_x.value(), self.spin_photo_y.value(),
                     self.spin_photo_w.value(), self.spin_photo_h.value())
        self.template.photo.place_on_badge = new_place
        if new_place != old_place:
            # область изменилась — подгоняем кадр под пропорции
            self._apply_place_from_preview(new_place)
        self.template.photo.face_scale = self.spin_face_scale.value()
        self.template.photo.face_offset_y = self.spin_face_offset.value()
        self.template.photo.remove_background = self.check_remove_bg.isChecked()
        self.template.photo.remove_bg_mode = self.combo_bg_mode.currentData() or "grabcut"
        self.template.photo.remove_bg_threshold = self.spin_bg_threshold.value()
        self._photo_params_dirty = True
        # фон/порог влияют на исходное фото — сбрасываем кэш примера,
        # чтобы Badge пересоздался с новыми параметрами
        self._example_badge = None
        self._update_preview()
        if self.tabs.currentIndex() == 1:
            self._update_example_preview(force_crop=True)

    # ------------------------------------------------------------------ #
    # Работа с превью
    # ------------------------------------------------------------------ #
    def _compute_preview_scale(self) -> float:
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

        scale = self._compute_preview_scale()
        self._preview_scale = scale
        if scale < 1.0:
            preview = preview.resize((max(1, round(preview.width * scale)),
                                      max(1, round(preview.height * scale))),
                                     Image.Resampling.LANCZOS)
        self.preview_label.set_scale(scale)
        self.preview_label.setPixmap(pil_to_pixmap(preview))

        # живой пример итогового бейджа (если вкладка активна)
        if self.tabs.currentIndex() == 1:
            self._update_example_preview(force_crop=False)

    def _on_preview_click(self, tx: int, ty: int) -> None:
        """Клик: если попали в элемент — захватываем его для перетаскивания
        (с сохранением смещения точки клика), иначе — ставим элемент в точку."""
        tw, th = self.template.size
        tx = min(max(0, tx), tw)
        ty = min(max(0, ty), th)
        # размер уголка в координатах макета (на превью он всегда ~16 px)
        handle = CORNER_HANDLE_SIZE / max(self._preview_scale, 1e-6)
        if self._mode == "photo":
            x, y, w, h = self.template.photo.place_on_badge
            on_corner = abs(tx - (x + w)) <= handle and abs(ty - (y + h)) <= handle
            inside = x <= tx <= x + w and y <= ty <= y + h
            if on_corner:
                self._drag = "photo_resize"
            elif inside:
                self._drag = "photo_move"  # элемент остаётся на месте — «хватаем»
            else:
                self._apply_place_from_preview((tx, ty, w, h))
                self._drag = "photo_move"
        else:
            field = self._current_field()
            if field is not None:
                box_w = field.max_width or int(tw * 0.3)
                box_h = max(20, int(field.font_size * 1.3))
                ax, ay = field.anchor
                inside = ax <= tx <= ax + box_w and ay <= ty <= ay + box_h
                if inside:
                    self._drag = "field_move"  # элемент остаётся на месте
                else:
                    field.anchor = (tx, ty)
                    self._drag = "field_move"
                self._sync_field_controls()
        self._update_preview()

    def _on_preview_move(self, dx: int, dy: int) -> None:
        if self._drag is None:
            return
        tw, th = self.template.size
        if self._drag == "photo_move":
            x, y, w, h = self.template.photo.place_on_badge
            nx = min(max(0, x + dx), tw - 1)
            ny = min(max(0, y + dy), th - 1)
            self._apply_place_from_preview((nx, ny, w, h))
        elif self._drag == "photo_resize":
            x, y, w, h = self.template.photo.place_on_badge
            nw = min(max(1, w + dx), tw - x)
            nh = min(max(1, h + dy), th - y)
            self._apply_place_from_preview((x, y, nw, nh))
        elif self._drag == "field_move":
            field = self._current_field()
            if field is not None:
                ax, ay = field.anchor
                field.anchor = (min(max(0, ax + dx), tw), min(max(0, ay + dy), th))
                self._sync_field_controls()
        self._update_preview()

    def _on_preview_released(self) -> None:
        self._drag = None
        if self.tabs.currentIndex() == 1:
            self._update_example_preview(force_crop=self._photo_params_dirty)

    def _sync_photo_spins(self) -> None:
        x, y, w, h = self.template.photo.place_on_badge
        for spin, value in ((self.spin_photo_x, x), (self.spin_photo_y, y),
                            (self.spin_photo_w, w), (self.spin_photo_h, h)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _sync_crop_spins(self) -> None:
        cw, ch = self.template.photo.crop_size
        for spin, value in ((self.spin_crop_w, cw), (self.spin_crop_h, ch)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _on_name_format_changed(self) -> None:
        """Переключение «Слушатель / Педсостав»: меняет name_format и
        добавляет/оставляет поле «Должность» (position)."""
        staff = self.radio_staff.isChecked()
        self.template.name_format = "staff" if staff else "listener"
        if staff and self.template.get_text_field("position") is None:
            surname = self.template.get_text_field("surname")
            anchor = (surname.anchor[0], surname.anchor[1] + int(surname.font_size * 1.5))
            self.template.text_fields.append(TextFieldConfig({
                "id": "position",
                "label": "Должность",
                "anchor": anchor,
                "align": "center",
                "font": "assets/Montserrat.ttf",
                "font_size": max(40, int(surname.font_size * 0.65)),
                "max_width": surname.max_width,
                "auto_shrink": True,
                "uppercase": False,
                "lowercase": True,
            }, self.template.config_dir))
        self._rebuild_fields_list()
        self._rebuild_mode_combo()
        if staff:
            # авто-выбор поля «Должность»: сразу можно двигать его на макете
            for i, f in enumerate(self.template.text_fields):
                if f.id == "position":
                    self.fields_list.setCurrentRow(i)  # вызовет _on_field_selected
                    break
        self._sync_field_controls()
        self._update_hint()
        self._update_preview()
        if self.tabs.currentIndex() == 1:
            self._update_example_preview(force_crop=False)

    def _sync_face_spins(self) -> None:
        for spin, value in ((self.spin_face_scale, self.template.photo.face_scale),
                            (self.spin_face_offset, self.template.photo.face_offset_y)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    def _auto_fit_crop(self, compensate_scale: bool = False) -> None:
        """Подгоняет кадр (crop_size) под пропорции области фото на макете,
        чтобы фото заполняло область без белых полей."""
        x, y, w, h = self.template.photo.place_on_badge
        cw, ch = self.template.photo.crop_size
        if w <= 0 or h <= 0 or cw <= 0 or ch <= 0:
            return
        area = cw * ch
        new_h = int(round((area * h / w) ** 0.5))
        new_w = int(round(new_h * w / h))
        if compensate_scale and cw > 0:
            self.template.photo.face_scale = (
                self.template.photo.face_scale * cw / max(1, new_w))
        self.template.photo.crop_size = (max(1, new_w), max(1, new_h))
        self._sync_crop_spins()
        self._sync_face_spins()

    def _apply_place_from_preview(self, place) -> None:
        """Обновляет область фото и автоматически подгоняет кадр под её
        пропорции, чтобы фото заполняло область без белых полей.

        При изменении ширины кадра компенсируем face_scale обратно
        пропорционально, чтобы лицо на итоговом бейдже сохранило размер.
        """
        self.template.photo.place_on_badge = place
        self._auto_fit_crop(compensate_scale=True)
        self._sync_photo_spins()
        self._sync_crop_spins()
        self._sync_face_spins()
        self._photo_params_dirty = True

    # ------------------------------------------------------------------ #
    # Пример итогового бейджа
    # ------------------------------------------------------------------ #
    def _fill_example_photo_combo(self) -> None:
        self.combo_example_photo.blockSignals(True)
        self.combo_example_photo.clear()
        for p in self._photos:
            self.combo_example_photo.addItem(Path(p).name, p)
        if self._photos:
            self.combo_example_photo.setCurrentIndex(0)
            self._example_photo = self._photos[0]
        self.combo_example_photo.blockSignals(False)

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self._update_example_preview(force_crop=True)

    def _on_example_photo_changed(self, index: int) -> None:
        if index < 0:
            return
        path = self.combo_example_photo.itemData(index)
        if path:
            self._example_photo = path
            self._example_badge = None
            self._update_example_preview(force_crop=True)

    def _pick_example_photo(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите фото для примера", "", "Изображения (*.png *.jpg *.jpeg)")
        if not filename:
            return
        self._example_photo = filename
        self._example_badge = None
        if filename not in self._photos:
            self.combo_example_photo.addItem(Path(filename).name, filename)
        self.combo_example_photo.setCurrentIndex(self.combo_example_photo.findData(filename))
        self._update_example_preview(force_crop=True)

    def _ensure_example_badge(self):
        """Создаёт Badge по выбранному фото (один раз на фото)."""
        if self._example_photo is None:
            return None
        if self._example_badge is not None and self._example_badge.get_url() == self._example_photo:
            return self._example_badge
        from badge_generator.BadgeGenerator import Badge
        try:
            self._example_badge = Badge(0, self._example_photo, self.template)
            self._photo_params_dirty = True
        except Exception as e:  # noqa: BLE001 — битое фото не должно ронять мастер
            self.example_label.setText(f"Не удалось построить пример бейджа: {e}")
            self._example_badge = None
        return self._example_badge

    def _update_example_preview(self, force_crop: bool = False) -> None:
        if self._example_photo is None:
            self.example_label.setText("Выберите фото, чтобы увидеть пример бейджа")
            self.example_label.setPixmap(QtGui.QPixmap())
            self.example_info.setText("")
            return
        badge = self._ensure_example_badge()
        if badge is None:
            return
        if force_crop:
            badge.apply_face_crop()
            self._photo_params_dirty = False
        badge.render()
        pixmap = pil_to_pixmap(badge.get_preview_image((460, 320)))
        self.example_label.setPixmap(pixmap)
        self.example_info.setText(
            f"Пример: {Path(self._example_photo).name}. Имя и фамилия берутся "
            "из названия файла; порядок полей можно поменять на вкладке "
            "«Расстановка элементов».")

    # ------------------------------------------------------------------ #
    # Быстрая настройка по готовому бейджу
    # ------------------------------------------------------------------ #
    def _quick_config_from_ready(self) -> None:
        ready, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Выберите готовый бейдж (пример результата)",
            "", "Изображения (*.png *.jpg *.jpeg)")
        if not ready:
            return
        from tools.derive_config import generate_config, save_config
        try:
            config = generate_config(self._template_path, Path(ready))
            # сохраняем тип бейджа и поле «Должность», если они уже были
            config["name_format"] = self.template.name_format
            if self.template.get_text_field("position") is not None:
                config.setdefault("text_fields", []).append(
                    self.template.get_text_field("position").to_dict())
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Не удалось настроить", str(e))
            return
        except Exception as e:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Не удалось настроить", f"Ошибка: {e}")
            return
        self.template = BadgeTemplate(self._template_path, config)
        self._sync_controls_from_template()
        self._rebuild_mode_combo()
        self._update_preview()
        self._photo_params_dirty = True
        QtWidgets.QMessageBox.information(
            self, "Готово",
            "Координаты текста и фото определены автоматически. Проверьте "
            "поля на превью (вкладка «Расстановка элементов»), при необходимости "
            "поправьте и нажмите «Сохранить конфиг».")

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
