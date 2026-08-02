from PIL import Image
import numpy as np
from pathlib import Path

IMAGE_SIZE_W = 555
PAGE_SIZE_W = 1534
IMAGE_SIZE_H = 771
PAGE_SIZE_H = 2140
IMAGE_ROW = 2
IMAGE_COLUMN = 2

def images_to_pdf(images_list, path_to_upload):
    if len(images_list) > 0:
        opened_images = []
        converted_images = []
        for current_im in images_list:
            opened_images.append(current_im)
        while len(opened_images) > 0:
            to_image = Image.new('RGB', (PAGE_SIZE_W, PAGE_SIZE_H), "white") #(IMAGE_COLUMN * IMAGE_SIZE_W, IMAGE_ROW * IMAGE_SIZE_H), "white")
            for y in range(1, IMAGE_ROW + 1):
                for x in range(1, IMAGE_COLUMN + 1):
                    if len(opened_images) > 0:
                        image = opened_images.pop()
                        from_image = image.resize((IMAGE_SIZE_W, IMAGE_SIZE_H), Image.LANCZOS)
                        to_image.paste(from_image, ((x - 1) * IMAGE_SIZE_W, (y - 1) * IMAGE_SIZE_H))
            converted_images.append(to_image.convert('RGB'))
        converted_images[0].save(path_to_upload, save_all=True, append_images=converted_images[1:])
        
if __name__ == "__main__":
    images_list = []
    for img_file in Path("../all_badges").glob("*.png"):
        image = Image.open(img_file)
        images_list.append(image)
        images_to_pdf(images_list, "../all_badges/badges_list.pdf")
    print(len(images_list))