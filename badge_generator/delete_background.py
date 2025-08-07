import glob
import os
from rembg import remove
from PIL import Image
from pathlib import Path

def remove_background(input_path: Path, output_path: Path):
    print(input_path)
    img = Image.open(input_path)
    result = remove(img)
    result.save(output_path, "PNG")

if __name__ == "__main__":
    for img_file in Path("../test/").glob("*.jpg"):
        out = Path("output") / "no_bg" / (img_file.stem + ".jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        remove_background(img_file, out)
    # full_pattern = os.path.join(".", "*")
    # matching_files = glob.glob(full_pattern)
    # for file_path in matching_files:
    #     print(file_path) # Print only the filename