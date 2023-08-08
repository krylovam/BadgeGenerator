from PIL import Image, ImageFont, ImageDraw
from PIL.ImageQt import ImageQt
from PyQt5.Qt import *
from PyQt5 import QtCore
from detector.FaceDetection import FaceDetector
import numpy as np
import os
import re
PHOTO_WIDTH = 168
PHOTO_HEIGHT = 214

class Badge:
    def __init__(self, id, url, template_url):
        self._id = id
        self._url = url
        self._template_url = template_url
        self._coords = {}
        self._name = ''
        self._surname = ''
        self._fontsize = 26
        self._name_coord_y = 323
        self._surname_coord_y = 353
        self._photo_x = 0
        self._photo_y = 0
        self._scale = 1.0
        self.init_name()
        print(self._name, self._surname)
        self.add_text()
        self.load_photo()
        #self.remove_background_color()
        self.detect_face()
        self.add_photo()
        #self._template.show()
        #self._template_photo.show()

    def init_name(self):
        self._url = self._url.replace('\\', '/')
        tmp = re.split('/', self._url)[-1]
        tmp = tmp.split('.')[0]
        surname, name = tmp.split(' ')
        self._name = name.title()
        self._surname = surname.title()

    def detect_face(self):
        detector = FaceDetector(self._url)
        detector.detect()
        x, y, w, h = detector.get_boxes()
        center_x, center_y = x + w / 2, y + h / 2
        scale = 0.5 * PHOTO_WIDTH / w
        new_size_x = round(self._photo.size[0] * scale)
        new_size_y = round(self._photo.size[1] * scale)
        self._photo = self._photo.resize((new_size_x, new_size_y))
        center_x *= scale
        center_y *= scale * 1.1
        if center_x < PHOTO_WIDTH / 2:
            self._photo_x = 0
        else:
            self._photo_x = int(center_x - PHOTO_WIDTH / 2)
        if center_y < PHOTO_HEIGHT / 2:
            self._photo_y = 0
        else:
            self._photo_y = int(center_y - PHOTO_HEIGHT / 2)

    def load_template(self):
        self._template = Image.open(self._template_url)

    def load_photo(self):
        self._photo = Image.open(self._url)

    def set_coords(self, coords):
        self._coords = coords

    def get_url(self):
        return self._url

    def get_name(self):
        return self._name

    def get_surname(self):
        return self._surname

    def get_photo_coords(self):
        return (self._photo_x, self._photo_y)

    def add_text(self):
        self.load_template()
        name_len = len(self._name)
        surname_len = len(self._surname)

        symbol_len = max(len(self._name), len(self._surname))
        # if symbol_len > 11:
            # self._fontsize = 20
            # self._name_coords = (110, 975)
            # self._surname_coords = (110, 885)
        font = ImageFont.truetype('../assets/Montserrat.ttf', size=self._fontsize)
        draw_name = ImageDraw.Draw(self._template)
        _, _, w, h = draw_name.textbbox((0, 0), self._name, font=font)
        W, H = self._template.size
        draw_name.text(
            ((W-w)/2, self._name_coord_y),
            self._name,
            font=font,
            fill=(255,255,255,255))
        draw_surname = ImageDraw.Draw(self._template)
        _, _, w, h = draw_surname.textbbox((0, 0), self._surname, font=font)
        draw_surname.text(
            ((W-w)/2, self._surname_coord_y),
            self._surname,
            font=font,
            fill=(255,255,255,255))

    def add_photo(self):
        self._template_photo = self._template.copy()
        self._photo_cropped = self._photo.crop((self._photo_x, self._photo_y,
                                               self._photo_x + PHOTO_WIDTH, self._photo_y + PHOTO_HEIGHT))
        self._template_photo.paste(self._photo_cropped, (86, 73)) # mask=self._photo_cropped)

    def get_badge(self):
        image = self._template_photo.convert("RGBA")
        qim = ImageQt(image)
        pixmap = QPixmap(QImage(qim))
        pixmap = pixmap.scaled(720, 480, QtCore.Qt.KeepAspectRatio)
        return pixmap

    def save_badge(self):
        dir_path = os.path.dirname(__file__)
        if not os.path.exists(f'{dir_path}/../ready-badges'):
            os.makedirs(f'{dir_path}/../ready-badges')
        self._template_photo.save(f'{dir_path}/../ready-badges/' + self._name + "_" + self._surname + "_badge.png")

    def get_photo(self):
        return self._template_photo

    def translate_photo(self, shift_x, shift_y):
        self._photo_x += shift_x * 5
        self._photo_y += shift_y * 5
        self.add_photo()

    def scale_photo(self, sign):
        size = self._photo.size
        if (sign == 1) :
            scale = 1.05
        else:
            scale = 0.95238095
        new_size = (round(size[0] * scale), round(size[1] * scale ))
        self._photo = self._photo.resize(new_size, Image.ANTIALIAS)
        self._photo_x *= scale
        self._photo_y *= scale
        self.add_photo()
