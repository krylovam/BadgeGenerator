import cv2


class FaceDetector:
    def __init__(self, path):
        self.face_cascade = cv2.CascadeClassifier('utils/cascade.xml')
        self.img = cv2.imread(path)
        self.gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
    def detect(self):
        self.faces = self.face_cascade.detectMultiScale(self.gray, 1.1, 7)
    
    def show_img(self):
        for (x, y, w, h) in self.faces:
            cv2.rectangle(self.img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        cv2.imshow('img', self.img)
        cv2.waitKey()


if __name__ == "__main__":
    detector = FaceDetector('andrey.jpeg')
    detector.detect()
    detector.show_img()