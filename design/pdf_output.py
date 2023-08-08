from PIL import Image

PAGE_SIZE_W = 2100
PAGE_SIZE_H = 2920
IMAGE_SIZE_W = 900
IMAGE_SIZE_H = 1200
IMAGE_ROW = 2
IMAGE_COLUMN = 2
SEP_SIZE=20

def images_to_pdf(images_list, path_to_upload):
    if len(images_list) > 0:
        opened_images = []
        converted_images = []
        for current_im in images_list:
            opened_images.append(current_im)
        while len(opened_images) > 0:
            to_image = Image.new('RGB', (PAGE_SIZE_W, PAGE_SIZE_H), "white")
            for y in range(1, IMAGE_ROW + 1):
                for x in range(1, IMAGE_COLUMN + 1):
                    if len(opened_images) > 0:
                        curr_im = opened_images.pop()
                        from_image = curr_im.resize((IMAGE_SIZE_W, IMAGE_SIZE_H), Image.ANTIALIAS)
                        to_image.paste(from_image, ((x - 1) * IMAGE_SIZE_W + (x - 1) * SEP_SIZE,
                                                    (y - 1) * IMAGE_SIZE_H + (y - 1) * SEP_SIZE))
            converted_images.append(to_image.convert('RGB'))
        converted_images[0].save(path_to_upload, save_all=True, append_images=converted_images[1:])