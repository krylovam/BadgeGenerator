"""Главный контроллер: связывает главное меню, конструктор и сохранение."""
from __future__ import annotations

import os
import sys

# Позволяет запускать как `python design/application_controller.py`, так и
# `python -m design.application_controller` из корня репозитория.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets

from design.constructor_controller import Constructor
from design.main_menu import MainMenu
from design.saver_controller import Saver


class Controller:
    def __init__(self):
        self.main_menu: MainMenu | None = None
        self.constructor: Constructor | None = None
        self.saver: Saver | None = None

    def show_main_menu(self):
        if self.saver is not None:
            self.saver.close()
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
    controller = Controller()
    controller.show_main_menu()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
