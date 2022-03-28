from PIL import Image

IMAGE_SIZE_W = 257
IMAGE_SIZE_H = 141
IMAGE_ROW = 5
IMAGE_COLUMN = 2


def images_to_pdf(images_list, path_to_upload):
    if len(images_list) > 0:
        opened_images = []
        converted_images = []
        for current_im in images_list:
            opened_images.append(Image.open(current_im))
        while len(opened_images) > 0:
            to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE_W, IMAGE_ROW * IMAGE_SIZE_H), "white")

            for y in range(1, IMAGE_ROW + 1):
                for x in range(1, IMAGE_COLUMN + 1):
                    if len(opened_images) > 0:
                        from_image = opened_images.pop().resize((IMAGE_SIZE_W, IMAGE_SIZE_H), Image.ANTIALIAS)
                        to_image.paste(from_image, ((x - 1) * IMAGE_SIZE_W, (y - 1) * IMAGE_SIZE_H))

            converted_images.append(to_image.convert('RGB'))
        converted_images[0].save(path_to_upload, save_all=True, append_images=converted_images[1:])
