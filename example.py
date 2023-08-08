import sys
import numpy as np
from PyQt5.Qt import *
from design.pdf_output import images_to_pdf
from PIL import Image


class Example(QWidget):
    def __init__(self):
        super().__init__()

        image = PIL.Image.open('a.png')
        image = image.convert("RGBA")

        images = []
        images.append(image)
        images_to_pdf(images, "C:/Users/krylo/PycharmProjects/BadgeGenerator/venv/tests/assets/")


if __name__ == '__main__':
    image = Image.open('C:/Users/krylo/PycharmProjects/path/BadgeGenerator/ready-badges/2отряд/Сергей_Артамонов_badge.png', mode='r')
    images = []
    images.append(image)
    images_to_pdf(images, "C:/Users/krylo/PycharmProjects/path/BadgeGenerator/ready-badges/artamonov.pdf")