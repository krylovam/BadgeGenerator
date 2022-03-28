from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setMinimumSize(1200, 700)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.pushButton_separate = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_separate.setGeometry(QtCore.QRect(450, 75, 300, 96))
        self.pushButton_separate.setObjectName("pushButton_separate")
        self.pushButton_union = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_union.setGeometry(QtCore.QRect(450, 200, 300, 96))
        self.pushButton_union.setObjectName("pushButton_union")
        self.pushButton_start_over = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_start_over.setGeometry(QtCore.QRect(450, 325, 300, 96))
        self.pushButton_start_over.setObjectName("pushButton_start_over")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 683, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton_separate.setText(_translate("MainWindow", "Сохранить бейджи по отдельности"))
        self.pushButton_union.setText(_translate("MainWindow", "Сохранить бейджи группой"))
        self.pushButton_start_over.setText(_translate("MainWindow", "Вернуться в начало"))
