from desings.saver import Ui_MainWindow

import sys
from PIL.ImageQt import ImageQt
from PyQt5.Qt import *
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import (QWidget, QPushButton, QMainWindow, QApplication)

class Saver(QtWidgets.QMainWindow):
    def __init__(self):
        super(Saver, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.pushButton_separate.clicked.connect(self.btn_save_templates)
        self.ui.pushButton_union.clicked.connect(self.btn_save_group)

    def btn_save_templates(self):
        print("Save badges separately")

    def btn_save_group(self):
        print("Save badges as group")
