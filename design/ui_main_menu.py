# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_menu.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMenuBar, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QStatusBar,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(900, 640)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.main_layout = QVBoxLayout(self.centralwidget)
        self.main_layout.setSpacing(12)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.title_label = QLabel(self.centralwidget)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 22px; font-weight: bold;")

        self.main_layout.addWidget(self.title_label)

        self.content_layout = QHBoxLayout()
        self.content_layout.setObjectName(u"content_layout")
        self.left_column = QVBoxLayout()
        self.left_column.setObjectName(u"left_column")
        self.label_step1 = QLabel(self.centralwidget)
        self.label_step1.setObjectName(u"label_step1")
        self.label_step1.setStyleSheet(u"font-weight: bold;")

        self.left_column.addWidget(self.label_step1)

        self.pushButton_photos = QPushButton(self.centralwidget)
        self.pushButton_photos.setObjectName(u"pushButton_photos")

        self.left_column.addWidget(self.pushButton_photos)

        self.label_photos_info = QLabel(self.centralwidget)
        self.label_photos_info.setObjectName(u"label_photos_info")

        self.left_column.addWidget(self.label_photos_info)

        self.spacer_1 = QSpacerItem(20, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.left_column.addItem(self.spacer_1)

        self.label_step2 = QLabel(self.centralwidget)
        self.label_step2.setObjectName(u"label_step2")
        self.label_step2.setStyleSheet(u"font-weight: bold;")

        self.left_column.addWidget(self.label_step2)

        self.pushButton_template = QPushButton(self.centralwidget)
        self.pushButton_template.setObjectName(u"pushButton_template")

        self.left_column.addWidget(self.pushButton_template)

        self.label_template_info = QLabel(self.centralwidget)
        self.label_template_info.setObjectName(u"label_template_info")

        self.left_column.addWidget(self.label_template_info)

        self.pushButton_configure = QPushButton(self.centralwidget)
        self.pushButton_configure.setObjectName(u"pushButton_configure")
        self.pushButton_configure.setEnabled(False)

        self.left_column.addWidget(self.pushButton_configure)

        self.pushButton_quick_config = QPushButton(self.centralwidget)
        self.pushButton_quick_config.setObjectName(u"pushButton_quick_config")
        self.pushButton_quick_config.setEnabled(False)

        self.left_column.addWidget(self.pushButton_quick_config)

        self.group_badge_type = QGroupBox(self.centralwidget)
        self.group_badge_type.setObjectName(u"group_badge_type")
        self.type_layout = QVBoxLayout(self.group_badge_type)
        self.type_layout.setSpacing(4)
        self.type_layout.setObjectName(u"type_layout")
        self.radio_listener = QRadioButton(self.group_badge_type)
        self.radio_listener.setObjectName(u"radio_listener")
        self.radio_listener.setChecked(True)

        self.type_layout.addWidget(self.radio_listener)

        self.radio_staff = QRadioButton(self.group_badge_type)
        self.radio_staff.setObjectName(u"radio_staff")

        self.type_layout.addWidget(self.radio_staff)


        self.left_column.addWidget(self.group_badge_type)

        self.spacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.left_column.addItem(self.spacer_2)

        self.error_label = QLabel(self.centralwidget)
        self.error_label.setObjectName(u"error_label")
        self.error_label.setStyleSheet(u"color: #c0392b;")
        self.error_label.setWordWrap(True)

        self.left_column.addWidget(self.error_label)


        self.content_layout.addLayout(self.left_column)

        self.spacer_3 = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.content_layout.addItem(self.spacer_3)

        self.right_column = QVBoxLayout()
        self.right_column.setObjectName(u"right_column")
        self.label_preview_title = QLabel(self.centralwidget)
        self.label_preview_title.setObjectName(u"label_preview_title")

        self.right_column.addWidget(self.label_preview_title)

        self.label_preview = QLabel(self.centralwidget)
        self.label_preview.setObjectName(u"label_preview")
        self.label_preview.setMinimumSize(QSize(460, 320))
        self.label_preview.setFrameShape(QFrame.StyledPanel)
        self.label_preview.setAlignment(Qt.AlignCenter)

        self.right_column.addWidget(self.label_preview)

        self.pushButton_preview_example = QPushButton(self.centralwidget)
        self.pushButton_preview_example.setObjectName(u"pushButton_preview_example")
        self.pushButton_preview_example.setEnabled(False)

        self.right_column.addWidget(self.pushButton_preview_example)


        self.content_layout.addLayout(self.right_column)


        self.main_layout.addLayout(self.content_layout)

        self.spacer_4 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.spacer_4)

        self.pushButton_next = QPushButton(self.centralwidget)
        self.pushButton_next.setObjectName(u"pushButton_next")
        self.pushButton_next.setEnabled(False)
        self.pushButton_next.setMinimumSize(QSize(0, 44))

        self.main_layout.addWidget(self.pushButton_next)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u0413\u0435\u043d\u0435\u0440\u0430\u0442\u043e\u0440 \u0431\u0435\u0439\u0434\u0436\u0435\u0439", None))
        self.title_label.setText(QCoreApplication.translate("MainWindow", u"\u0413\u0435\u043d\u0435\u0440\u0430\u0442\u043e\u0440 \u0431\u0435\u0439\u0434\u0436\u0435\u0439", None))
        self.label_step1.setText(QCoreApplication.translate("MainWindow", u"1. \u041f\u0430\u043f\u043a\u0430 \u0441 \u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u044f\u043c\u0438 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432", None))
        self.pushButton_photos.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443 \u0441 \u0444\u043e\u0442\u043e", None))
        self.label_photos_info.setText(QCoreApplication.translate("MainWindow", u"\u0424\u043e\u0442\u043e: \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e", None))
        self.label_step2.setText(QCoreApplication.translate("MainWindow", u"2. \u041c\u0430\u043a\u0435\u0442 \u0431\u0435\u0439\u0434\u0436\u0430 (PNG)", None))
        self.pushButton_template.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0448\u0430\u0431\u043b\u043e\u043d", None))
        self.label_template_info.setText(QCoreApplication.translate("MainWindow", u"\u0428\u0430\u0431\u043b\u043e\u043d: \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d", None))
        self.pushButton_configure.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0448\u0430\u0431\u043b\u043e\u043d\u2026", None))
        self.pushButton_quick_config.setText(QCoreApplication.translate("MainWindow", u"\u0411\u044b\u0441\u0442\u0440\u0430\u044f \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043f\u043e \u0433\u043e\u0442\u043e\u0432\u043e\u043c\u0443 \u0431\u0435\u0439\u0434\u0436\u0443\u2026", None))
#if QT_CONFIG(tooltip)
        self.pushButton_quick_config.setToolTip(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0433\u043e\u0442\u043e\u0432\u044b\u0439 \u0431\u0435\u0439\u0434\u0436 (\u043f\u0440\u0438\u043c\u0435\u0440 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430) \u2014 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0441\u0430\u043c\u043e \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442 \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u044b \u0442\u0435\u043a\u0441\u0442\u0430 \u0438 \u0444\u043e\u0442\u043e \u0438 \u0441\u043e\u0437\u0434\u0430\u0441\u0442 \u043a\u043e\u043d\u0444\u0438\u0433", None))
#endif // QT_CONFIG(tooltip)
        self.group_badge_type.setTitle(QCoreApplication.translate("MainWindow", u"\u0422\u0438\u043f \u0431\u0435\u0439\u0434\u0436\u0430", None))
        self.radio_listener.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043b\u0443\u0448\u0430\u0442\u0435\u043b\u044c \u2014 2 \u043f\u043e\u043b\u044f (\u0438\u043c\u044f, \u0444\u0430\u043c\u0438\u043b\u0438\u044f)", None))
        self.radio_staff.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0435\u0434\u0441\u043e\u0441\u0442\u0430\u0432 \u2014 3 \u043f\u043e\u043b\u044f (+ \u0434\u043e\u043b\u0436\u043d\u043e\u0441\u0442\u044c)", None))
        self.error_label.setText("")
        self.label_preview_title.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u0435\u0432\u044c\u044e \u043c\u0430\u043a\u0435\u0442\u0430:", None))
        self.label_preview.setText(QCoreApplication.translate("MainWindow", u"\u041c\u0430\u043a\u0435\u0442 \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d", None))
        self.pushButton_preview_example.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u043f\u0440\u0438\u043c\u0435\u0440 \u0431\u0435\u0439\u0434\u0436\u0430 \u0441 \u0444\u043e\u0442\u043e", None))
#if QT_CONFIG(tooltip)
        self.pushButton_preview_example.setToolTip(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0431\u0440\u0430\u0442\u044c \u043f\u0440\u0438\u043c\u0435\u0440 \u0433\u043e\u0442\u043e\u0432\u043e\u0433\u043e \u0431\u0435\u0439\u0434\u0436\u0430: \u043f\u0435\u0440\u0432\u043e\u0435 \u0444\u043e\u0442\u043e \u0438\u0437 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0439 \u043f\u0430\u043f\u043a\u0438 + \u0438\u043c\u044f/\u0444\u0430\u043c\u0438\u043b\u0438\u044f \u0438\u0437 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f \u0444\u0430\u0439\u043b\u0430", None))
#endif // QT_CONFIG(tooltip)
        self.pushButton_next.setText(QCoreApplication.translate("MainWindow", u"\u0414\u0430\u043b\u044c\u0448\u0435 \u2192", None))
    # retranslateUi

