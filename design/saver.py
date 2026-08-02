"""Интерфейс сохранения результатов: отдельные PNG или PDF для печати."""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets


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
        self.label_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.label_preview.setFrameShape(QtWidgets.QFrame.StyledPanel)
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
        for b in (self.btn_save_separate, self.btn_save_pdf):
            b.setMinimumHeight(40)
        self.btn_start_over = QtWidgets.QPushButton("Вернуться в начало")
        buttons.addWidget(self.btn_save_separate)
        buttons.addWidget(self.btn_save_pdf)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_start_over)
        root.addLayout(buttons)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle("Сохранение бейджей")
