from PyQt5 import QtWidgets, uic
from desings.menu_window import Ui_MainWindow
import sys
import os
import os.path
from os.path import expanduser

class FilesData(object):
    def __init__(self):
        self.files_names = []
        self.template_name = ""

    def set_files_names(self, directory, list_of_names):
        self.files_names = []
        for filename in list_of_names:
            self.files_names.append(os.path.join(directory, filename))

    def set_template_name(self, template_name):
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

    def ObjectToArray(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        files_names = os.listdir(directory)
        self.DataDirectories.set_files_names(directory, files_names)

    def DownloadTemplateName(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Select file")
        self.DataDirectories.set_template_name(filename[0])

    def GetListOfFiles(self):
        return files_names