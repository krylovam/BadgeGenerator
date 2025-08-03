from PyQt6 import QtWidgets
from menu_window import Ui_MainWindow
import glob
import os

class FilesData(object):
    def __init__(self):
        self.file_paths = []
        self.template_path = ""

    def set_file_paths(self, directory):
        patterns = ['*.png', '*.jpeg', '*.jpg']
        self.file_paths = []
        for pattern in patterns:
            full_pattern = os.path.join(directory, pattern)
            matching_files = glob.glob(full_pattern)
            self.file_paths += [str(path) for path in matching_files]

    def set_template_path(self, template_path):
        if template_path.endswith(('.png')):
            self.template_path = template_path


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
        self.DataDirectories.set_file_paths(directory)
        self.CheckErrors()

    def DownloadTemplateName(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Select file")
        self.DataDirectories.set_template_path(filename[0])
        self.CheckErrors()

    def CheckErrors(self):
        if len(self.DataDirectories.file_paths) == 0:
            self.ui.error_label.setText("В выбранной папке нет фотографий")
            self.ui.pushButton_3.setEnabled(False)
        elif self.DataDirectories.template_path == "":
            self.ui.error_label.setText("Выбранный шаблон не png файл")
            self.ui.pushButton_3.setEnabled(False)
        else:
            self.ui.error_label.setText("")
            self.ui.pushButton_3.setEnabled(True)

