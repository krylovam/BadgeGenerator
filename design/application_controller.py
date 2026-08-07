"""Главный контроллер: связывает главное меню, конструктор и сохранение."""
from __future__ import annotations

import os
import sys

# Позволяет запускать как `python design/application_controller.py`, так и
# `python -m design.application_controller` из корня репозитория.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6 import QtWidgets

from design.constructor_controller import Constructor
from design.main_menu import MainMenu
from design.saver_controller import Saver

APP_STYLESHEET = """
QMainWindow, QDialog {
    background: #f4f6fb;
}
QLabel {
    color: #1e293b;
}
QPushButton {
    background: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background: #2563eb;
}
QPushButton:pressed {
    background: #1d4ed8;
}
QPushButton:disabled {
    background: #cbd5e1;
    color: #f8fafc;
}
QGroupBox {
    border: 1px solid #d7dee9;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 6px;
    font-weight: 600;
    color: #334155;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 8px;
    color: #1e293b;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #3b82f6;
}
QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-align: center;
    background: #ffffff;
}
QProgressBar::chunk {
    background: #3b82f6;
    border-radius: 5px;
}
QStatusBar {
    background: #e8ecf5;
}
QCheckBox {
    color: #334155;
}
"""


class Controller:
    def __init__(self):
        self.main_menu: MainMenu | None = None
        self.constructor: Constructor | None = None
        self.saver: Saver | None = None

    def show_main_menu(self):
        if self.saver is not None:
            self.saver.close()
        if self.constructor is not None:
            self.constructor.close()
        self.main_menu = MainMenu()
        self.main_menu.next_requested.connect(self.show_constructor)
        self.main_menu.show()

    def show_constructor(self):
        if self.main_menu is None or not self.main_menu.is_ready():
            return
        self.constructor = Constructor(self.main_menu.photos, self.main_menu.template)
        if not self.constructor.is_ready():
            # генерация не удалась или отменена — возвращаемся в меню
            self.constructor.close()
            self.show_main_menu()
            return
        self.constructor.finished.connect(self.show_saver)
        self.constructor.back_to_menu.connect(self.show_main_menu)
        self.main_menu.close()
        self.constructor.show()

    def show_saver(self):
        if self.constructor is None:
            return
        self.saver = Saver(self.constructor.badges)
        self.saver.restarted.connect(self.show_main_menu)
        self.constructor.close()
        self.saver.show()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    controller = Controller()
    controller.show_main_menu()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
