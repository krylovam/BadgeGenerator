from saver import Ui_MainWindow

from PyQt5 import QtWidgets
from pdf_output import images_to_pdf
import os

class Saver(QtWidgets.QMainWindow):
    def __init__(self, badges):
        super(Saver, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.badges = badges
        self.ui.pushButton_separate.clicked.connect(self.btn_save_templates)
        self.ui.pushButton_union.clicked.connect(self.btn_save_group)

    def btn_save_templates(self):
        for badge in self.badges:
            badge.save_badge()

    def btn_save_group(self):
        images = []
        for badge in self.badges:
            images.append(badge.get_photo())
        dir_path = os.path.dirname(__file__)
        if not os.path.exists(f'{dir_path}/../ready-badges'):
            os.makedirs(f'{dir_path}/../ready-badges')
        images_to_pdf(images, f'{dir_path}/../ready-badges/badges_list.pdf')


