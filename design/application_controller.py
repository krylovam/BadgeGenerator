from constructor_controller import Constructor
from saver_controller import Saver
from main_menu import MainMenu
import sys
from PyQt5 import QtCore, QtWidgets

class Controller:

    def __init__(self):
        self.main_menu = None
        self.constructor = None
        self.saver = None

    def show_main_menu(self):
        self.main_menu = MainMenu()
        self.main_menu.ui.pushButton_3.clicked.connect(self.show_constructor)
        if self.saver:
            self.saver.close()
        self.main_menu.show()

    def show_constructor(self):
        self.constructor = Constructor(self.main_menu.DataDirectories.files_names,
                                       self.main_menu.DataDirectories.template_name)
        self.constructor.ui.pushButton_finish.clicked.connect(self.show_saver)
        self.main_menu.close()
        self.constructor.show()

    def show_saver(self):
        self.saver = Saver()
        self.saver.ui.pushButton_start_over.clicked.connect(self.show_main_menu)
        self.constructor.close()
        self.saver.show()

def main():
    app = QtWidgets.QApplication(sys.argv)
    controller = Controller()
    controller.show_main_menu()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()