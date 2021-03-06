import cv2
import numpy as np
import os

class FaceDetector:
    def __init__(self, path):
        dir_path = os.path.dirname(__file__)
        self.face_cascade = cv2.CascadeClassifier(f'{dir_path}/utils/cascade.xml')
        self.img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)

    def detect(self):
        self.faces = self.face_cascade.detectMultiScale(self.gray, 1.1, 12)

    def show_img(self):
        for (x, y, w, h) in self.faces:
            cv2.rectangle(self.img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.imshow('img', self.img)
        cv2.waitKey()

    def get_boxes(self):
        assert len(self.faces) == 1
        return self.faces[0]

