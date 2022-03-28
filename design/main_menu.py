from PyQt5 import QtWidgets, uic
from desings.menu_window import Ui_MainWindow
import sys
import os
import os.path
from pathlib import Path

class FilesData(object):
    def __init__(self):
        self.files_names = []
        self.template_name = ""

    def set_files_names(self, directory):
        self.files_names = []
        frames = Path(directory)
        types = ['*.png', '*.jpeg']
        for type in types:
            for file in frames.glob(type):
                self.files_names.append(str(file))


    def set_template_name(self, template_name):
        if template_name.endswith(('.png')):
            self.template_name = template_name

    def print_files_data(self):
        print(self.files_names , "\n-----------\n", self.template_name)

class MainMenu(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainMenu, self).__init__()
        self.setWindowTitle("ConstructorMainMenu")
        self.setMinimumSize(1500, 800)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.DataDirectories = FilesData()

        self.ui.pushButton.clicked.connect(self.ObjectToArray)
        self.ui.pushButton_2.clicked.connect(self.DownloadTemplateName)
        self.ui.pushButton_3.setEnabled(False)

    def ObjectToArray(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        self.DataDirectories.set_files_names(directory)
        self.CheckErrors()

    def DownloadTemplateName(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Select file")
        self.DataDirectories.set_template_name(filename[0])
        self.CheckErrors()

    def CheckErrors(self):
        if len(self.DataDirectories.files_names) == 0:
            self.ui.error_label.setText("В выбранной папке нет фотографий")
            self.ui.pushButton_3.setEnabled(False)
        elif self.DataDirectories.template_name == "":
            self.ui.error_label.setText("Выбранный шаблон не png файл")
            self.ui.pushButton_3.setEnabled(False)
        else:
            self.ui.error_label.setText("")
            self.ui.pushButton_3.setEnabled(True)

    def GetListOfFiles(self):
        return files_names
