"""Интерфейс сохранения результатов: отдельные PNG или PDF для печати."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setMinimumSize(900, 700)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        root = QtWidgets.QVBoxLayout(self.centralwidget)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QtWidgets.QLabel("Сохранение результатов")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        self.label_info = QtWidgets.QLabel("")
        self.label_info.setStyleSheet("color: #555;")
        root.addWidget(self.label_info)

        root.addWidget(QtWidgets.QLabel("Предпросмотр первой страницы PDF:"))

        self.label_preview = QtWidgets.QLabel()
        self.label_preview.setMinimumSize(600, 400)
        self.label_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.label_preview.setText("Предпросмотр недоступен")
        root.addWidget(self.label_preview, stretch=1)

        options = QtWidgets.QHBoxLayout()
        self.check_cut_lines = QtWidgets.QCheckBox("Рисовать линии отреза в PDF")
        self.check_cut_lines.setChecked(True)
        options.addWidget(self.check_cut_lines)
        options.addStretch(1)
        root.addLayout(options)

        out_box = QtWidgets.QGroupBox("Папка для сохранения")
        out_row = QtWidgets.QHBoxLayout(out_box)
        self.edit_output_dir = QtWidgets.QLineEdit()
        self.btn_browse = QtWidgets.QPushButton("Обзор…")
        out_row.addWidget(self.edit_output_dir, stretch=1)
        out_row.addWidget(self.btn_browse)
        root.addWidget(out_box)

        self.label_status = QtWidgets.QLabel("")
        self.label_status.setWordWrap(True)
        root.addWidget(self.label_status)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_save_separate = QtWidgets.QPushButton("Сохранить отдельными PNG")
        self.btn_save_pdf = QtWidgets.QPushButton("Сохранить PDF для печати")
        self.btn_png_to_pdf = QtWidgets.QPushButton("PDF из готовых PNG…")
        for b in (self.btn_save_separate, self.btn_save_pdf, self.btn_png_to_pdf):
            b.setMinimumHeight(40)
        self.btn_start_over = QtWidgets.QPushButton("Вернуться в начало")
        buttons.addWidget(self.btn_save_separate)
        buttons.addWidget(self.btn_save_pdf)
        buttons.addWidget(self.btn_png_to_pdf)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_start_over)
        root.addLayout(buttons)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("Сохранение бейджей")


class PngToPdfDialog(QtWidgets.QDialog):
    """Диалог сборки PDF из выбранных PNG-файлов (готовых бейджей)."""

    def __init__(self, badge_size_mm=(100, 70), dpi=300,
                 output_dir="", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Собрать PDF из PNG")
        self.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            "Из выбранных PNG-файлов будет собран лист для печати "
            "(A4, линии отреза при необходимости)."))

        form = QtWidgets.QFormLayout()
        self.spin_w = QtWidgets.QSpinBox()
        self.spin_w.setRange(20, 500)
        self.spin_w.setSuffix(" мм")
        self.spin_w.setValue(int(badge_size_mm[0]))
        self.spin_h = QtWidgets.QSpinBox()
        self.spin_h.setRange(20, 500)
        self.spin_h.setSuffix(" мм")
        self.spin_h.setValue(int(badge_size_mm[1]))
        self.spin_dpi = QtWidgets.QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        self.spin_dpi.setSuffix(" dpi")
        self.spin_dpi.setValue(int(dpi))
        self.check_cut = QtWidgets.QCheckBox("Рисовать линии отреза")
        self.check_cut.setChecked(True)
        form.addRow("Ширина бейджа:", self.spin_w)
        form.addRow("Высота бейджа:", self.spin_h)
        form.addRow("Разрешение:", self.spin_dpi)
        form.addRow("", self.check_cut)
        layout.addLayout(form)

        out_box = QtWidgets.QGroupBox("Куда сохранить")
        out_row = QtWidgets.QHBoxLayout(out_box)
        self.edit_out = QtWidgets.QLineEdit(output_dir)
        self.btn_browse = QtWidgets.QPushButton("Обзор…")
        out_row.addWidget(self.edit_out, stretch=1)
        out_row.addWidget(self.btn_browse)
        layout.addWidget(out_box)
        self.btn_browse.clicked.connect(self._browse)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.btn_cancel = QtWidgets.QPushButton("Отмена")
        self.btn_ok = QtWidgets.QPushButton("Собрать PDF")
        self.btn_ok.setDefault(True)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_ok)
        layout.addLayout(buttons)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

    def _browse(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Сохранить PDF как", self.edit_out.text(), "PDF (*.pdf)")
        if filename:
            self.edit_out.setText(filename)

    def badge_size_mm(self) -> tuple:
        return self.spin_w.value(), self.spin_h.value()
