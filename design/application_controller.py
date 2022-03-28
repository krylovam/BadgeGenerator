from constructor_controller import Constructor
from main_menu import MainMenu
import sys
from PyQt5 import QtCore, QtWidgets

class Controller:

    def __init__(self):
        pass

    def show_main_menu(self):
        self.main_menu = MainMenu()
        self.main_menu.ui.pushButton_3.clicked.connect(self.show_constructor)
        self.main_menu.show()

    def show_constructor(self):
        self.constructor = Constructor(self.main_menu.DataDirectories.files_names,
                                       self.main_menu.DataDirectories.template_name)
        self.constructor.ui.pushButton_finish.clicked.connect(self.show_finish)
        self.main_menu.close()
        self.constructor.show()

    def show_finish(self):
        print("FINISH")

def main():
    app = QtWidgets.QApplication(sys.argv)
    controller = Controller()
    controller.show_main_menu()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()