"""Интерфейс конструктора: настройка фото на бейдже."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class _PreviewLabel(QtWidgets.QLabel):
    """Метка-превью с перетаскиванием мышью и зумом колёсиком."""

    translated = QtCore.Signal(int, int)  # сдвиг в координатах бейджа
    zoomed = QtCore.Signal(float)

    def __init__(self):
        super().__init__()
        self._scale = 1.0
        self._last: QtCore.QPoint | None = None
        self.setMouseTracking(True)
        self.setMinimumSize(720, 480)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setStyleSheet("background-color: #f2f2f2;")

    def set_scale(self, scale: float) -> None:
        """Соотношение пикселей pixmap к пикселям бейджа."""
        self._scale = scale

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._last = event.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._last is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            dx = event.pos().x() - self._last.x()
            dy = event.pos().y() - self._last.y()
            self._last = event.pos()
            if dx or dy:
                self.translated.emit(round(dx / self._scale), round(dy / self._scale))

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._last = None

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        factor = 1.05 if event.angleDelta().y() > 0 else 0.95238095
        self.zoomed.emit(factor)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setMinimumSize(1200, 760)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        root = QtWidgets.QVBoxLayout(self.centralwidget)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # --- шапка ----------------------------------------------------- #
        header = QtWidgets.QHBoxLayout()
        self.label_counter = QtWidgets.QLabel("Бейдж 0 из 0")
        self.label_counter.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.label_names = QtWidgets.QLabel("")
        self.label_names.setStyleSheet("font-size: 14px; color: #555;")
        header.addWidget(self.label_counter)
        header.addWidget(self.label_names)
        header.addStretch(1)
        self.check_apply_all = QtWidgets.QCheckBox("Применять правки ко всем бейджам")
        self.btn_undo = QtWidgets.QPushButton("Отменить (Ctrl+Z)")
        header.addWidget(self.check_apply_all)
        header.addWidget(self.btn_undo)
        root.addLayout(header)

        # --- превью ----------------------------------------------------- #
        self.preview_label = _PreviewLabel()
        root.addWidget(self.preview_label, stretch=1)

        # --- панель управления ----------------------------------------- #
        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(10)

        move_box = QtWidgets.QGroupBox("Положение фото")
        move_grid = QtWidgets.QGridLayout(move_box)
        self.btn_up = QtWidgets.QPushButton("▲")
        self.btn_down = QtWidgets.QPushButton("▼")
        self.btn_left = QtWidgets.QPushButton("◀")
        self.btn_right = QtWidgets.QPushButton("▶")
        for b in (self.btn_up, self.btn_down, self.btn_left, self.btn_right):
            b.setFixedSize(44, 44)
        move_grid.addWidget(self.btn_up, 0, 1)
        move_grid.addWidget(self.btn_left, 1, 0)
        move_grid.addWidget(self.btn_right, 1, 2)
        move_grid.addWidget(self.btn_down, 2, 1)
        controls.addWidget(move_box)

        zoom_box = QtWidgets.QGroupBox("Масштаб")
        zoom_v = QtWidgets.QVBoxLayout(zoom_box)
        self.btn_zoom_in = QtWidgets.QPushButton("+")
        self.btn_zoom_out = QtWidgets.QPushButton("−")
        for b in (self.btn_zoom_in, self.btn_zoom_out):
            b.setFixedSize(44, 44)
        zoom_v.addWidget(self.btn_zoom_in)
        zoom_v.addWidget(self.btn_zoom_out)
        controls.addWidget(zoom_box)

        name_box = QtWidgets.QGroupBox("Имя на бейдже")
        name_form = QtWidgets.QFormLayout(name_box)
        self.edit_surname = QtWidgets.QLineEdit()
        self.edit_name = QtWidgets.QLineEdit()
        self.edit_surname.setPlaceholderText("Фамилия")
        self.edit_name.setPlaceholderText("Имя")
        name_form.addRow("Фамилия:", self.edit_surname)
        name_form.addRow("Имя:", self.edit_name)
        self.btn_apply_name = QtWidgets.QPushButton("Применить")
        name_form.addRow("", self.btn_apply_name)
        controls.addWidget(name_box)

        # дополнительные текстовые поля из конфига шаблона
        self.extra_fields_box = QtWidgets.QGroupBox("Доп. поля")
        self.extra_fields_form = QtWidgets.QFormLayout(self.extra_fields_box)
        controls.addWidget(self.extra_fields_box)
        self.extra_fields_box.hide()

        controls.addStretch(1)
        root.addLayout(controls)

        # --- низ -------------------------------------------------------- #
        bottom = QtWidgets.QHBoxLayout()
        self.btn_back = QtWidgets.QPushButton("← Назад")
        self.btn_next = QtWidgets.QPushButton("Дальше →")
        for b in (self.btn_back, self.btn_next):
            b.setFixedHeight(40)
        bottom.addWidget(self.btn_back)
        bottom.addWidget(self.btn_next)
        bottom.addStretch(1)
        self.btn_to_menu = QtWidgets.QPushButton("В главное меню")
        self.btn_to_menu.setFixedHeight(40)
        bottom.addWidget(self.btn_to_menu)
        self.btn_finish = QtWidgets.QPushButton("Закончить редактирование")
        self.btn_finish.setFixedHeight(40)
        bottom.addWidget(self.btn_finish)
        root.addLayout(bottom)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("Настройка фото на бейджах")
        self.btn_up.setToolTip("Сдвинуть фото вверх")
        self.btn_down.setToolTip("Сдвинуть фото вниз")
        self.btn_left.setToolTip("Сдвинуть фото влево")
        self.btn_right.setToolTip("Сдвинуть фото вправо")
        self.btn_zoom_in.setToolTip("Увеличить фото")
        self.btn_zoom_out.setToolTip("Уменьшить фото")
        self.btn_finish.setText("Закончить редактирование")
