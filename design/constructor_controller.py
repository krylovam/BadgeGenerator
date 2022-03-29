import sys
import os
sys.path.append(os.path.dirname(__file__) + '/..')
from badge_generator.BadgeGenerator import Badge
from constructor import Ui_MainWindow

import glob
import sys
from PIL import Image, ImageOps, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt5.Qt import *
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import (QWidget, QPushButton,
    QHBoxLayout, QVBoxLayout, QApplication)

class Constructor(QtWidgets.QMainWindow):
    def __init__(self, urls, template_url):
        super(Constructor, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_badges(urls, template_url)
        self.curr_badge_id = 0
        self.badge = self.badges[self.curr_badge_id ]
        self.badge_label = QLabel()
        self.badge_label.setPixmap(self.badge.get_badge())

        self.ui.verticalLayout.addWidget(self.badge_label)
        self.ui.pushButton_up.clicked.connect(self.btn_up_clicked)
        self.ui.pushButton_down.clicked.connect(self.btn_down_clicked)
        self.ui.pushButton_left.clicked.connect(self.btn_left_clicked)
        self.ui.pushButton_right.clicked.connect(self.btn_right_clicked)
        self.ui.pushButton_plus.clicked.connect(self.btn_plus_clicked)
        self.ui.pushButton_minus.clicked.connect(self.btn_minus_clicked)
        self.ui.pushButton_next.clicked.connect(self.btn_next_clicked)
        self.ui.pushButton_back.clicked.connect(self.btn_back_clicked)

    def init_badges(self, urls, template_url):
        self.badges = []
        for i, url in enumerate(urls):
            badge = Badge(i, url, template_url)
            self.badges.append(badge)

    def btn_up_clicked(self):
        self.translate_photo(0, 1)

    def btn_down_clicked(self):
        self.translate_photo(0, -1)

    def btn_left_clicked(self):
        self.translate_photo(-1, 0)

    def btn_right_clicked(self):
        self.translate_photo(1, 0)

    def btn_plus_clicked(self):
        self.scale_photo(True)

    def btn_minus_clicked(self):
        self.scale_photo(False)

    def btn_next_clicked(self):
        self.curr_badge_id += 1
        if self.curr_badge_id >= len(self.badges):
            return
        self.ui.verticalLayout.itemAt(0).widget().deleteLater()
        self.badge = self.badges[self.curr_badge_id]
        self.badge_label = QLabel()
        self.badge_label.setPixmap(self.badge.get_badge())
        self.ui.verticalLayout.addWidget(self.badge_label)

    def btn_back_clicked(self):
        if self.curr_badge_id == 0:
            return
        self.curr_badge_id -= 1
        self.ui.verticalLayout.itemAt(0).widget().deleteLater()
        self.badge = self.badges[self.curr_badge_id]
        self.badge_label = QLabel()
        self.badge_label.setPixmap(self.badge.get_badge())
        self.ui.verticalLayout.addWidget(self.badge_label)

    def translate_photo(self, shift_x, shift_y):
        self.ui.verticalLayout.itemAt(0).widget().deleteLater()
        self.badge.translate_photo(-shift_x, shift_y)
        self.badges[self.curr_badge_id] = self.badge
        self.badge_label = QLabel()
        self.badge_label.setPixmap(self.badge.get_badge())
        self.ui.verticalLayout.addWidget(self.badge_label)

    def scale_photo(self, is_enlarge):
        self.ui.verticalLayout.itemAt(0).widget().deleteLater()
        self.badge.scale_photo(is_enlarge)
        self.badges[self.curr_badge_id] = self.badge
        self.badge_label = QLabel()
        self.badge_label.setPixmap(self.badge.get_badge())
        self.ui.verticalLayout.addWidget(self.badge_label)
