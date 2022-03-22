from PIL import Image, ImageFont, ImageDraw
from PIL.ImageQt import ImageQt
from PyQt5.Qt import *

class Badge:
    def __init__(self, id, url, template_url):
        self._id = id
        self._url = url
        self._template_url = template_url
        self._coords = {}
        self._name = ''
        self._surname = ''
        self._fontsize = 75
        self._name_coords = (600, 100)
        self._surname_coords = (600, 225)
        self._photo_x = 0
        self._photo_y = 0
        self._scale = 1.0
        self.init_name()
        self.add_text()
        self.add_photo()
        #self._template.show()
        #self._template_photo.show()

    def init_name(self):
        tmp = self._url.split('/')[-1]
        tmp = tmp.split('.')[0]
        surname, name = tmp.split('_')
        self._name = name.title()
        self._surname = surname.title()

    def load_template(self):
        self._template = PIL.Image.open(self._template_url)

    def load_image(self):
        self._photo = PIL.Image.open(self._url)

    def set_coords(self, coords):
        self._coords = coords

    def get_url(self):
        return self._url

    def get_name(self):
        return self._name

    def get_surname(self):
        return self._surname

    def add_text(self):
        self._template = Image.open(self._template_url)
        symbol_len = max(len(self._name), len(self._surname))
        if symbol_len > 11:
            self._fontsize = 60
            self._name_coords = (570, 100)
            self._surname_coords = (570, 225)
        font = ImageFont.truetype('C:/Users/krylo/PycharmProjects/BadgeGenerator/Montserrat.ttf', size=self._fontsize)
        draw_name = ImageDraw.Draw(self._template)
        draw_name.text(
            self._name_coords,
            self._name,
            font=font,
            fill='#3a393d')
        draw_surname = ImageDraw.Draw(self._template)
        draw_surname.text(
            self._surname_coords,
            self._surname,
            font=font,
            fill='#3a393d')

    def add_photo(self):
        self._photo = Image.open(self._url)
        self._template_photo = self._template.copy()
        self._photo_x = 140
        self._photo_y = 180
        self._photo_cropped = self._photo.crop((self._photo_x, self._photo_y,
                                               self._photo_x + 341, self._photo_y + 469))
        self._template_photo.paste(self._photo_cropped, (94, 92), self._photo_cropped)

    def get_badge(self):
        qim = ImageQt(self._template_photo)
        pixmap = QPixmap(QImage(qim))
        label = QLabel()
        label.setPixmap(pixmap)
        return label


