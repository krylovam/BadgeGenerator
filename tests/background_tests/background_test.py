"""Тесты вырезания человека библиотекой rembg."""
import os

import numpy as np
import pytest
from PIL import Image

from badge_generator.delete_background import remove_background_rembg

dir_path = os.path.dirname(__file__)


def _rembg_model_available() -> bool:
    """rembg по умолчанию использует модель u2net.onnx из U2NET_HOME
    (~/.u2net). Если её нет — не пытаемся качать из интернета в CI."""
    home = os.environ.get("U2NET_HOME", os.path.join(os.path.expanduser("~"), ".u2net"))
    return os.path.isfile(os.path.join(home, "u2net.onnx")) or \
        os.path.isfile(os.path.join(home, "u2netp.onnx"))


@pytest.mark.skipif(not _rembg_model_available(), reason="модель rembg не найдена")
def test_rembg_returns_rgba() -> None:
    """remove_background_rembg возвращает RGBA-изображение того же размера."""
    img = Image.new("RGB", (100, 120), (200, 200, 200))
    result = remove_background_rembg(img)
    assert result.mode == "RGBA"
    assert result.size == (100, 120)


@pytest.mark.skipif(not _rembg_model_available(), reason="модель rembg не найдена")
def test_rembg_cuts_person_on_real_photo() -> None:
    """rembg вырезает человека: лицо непрозрачно, углы прозрачны."""
    import sys
    sys.path.insert(0, os.path.join(dir_path, "..", ".."))
    from detector.FaceDetection import FaceDetector

    photo = os.path.join(dir_path, "..", "assets", "photos", "judy_estrin.jpeg")
    rgba = remove_background_rembg(Image.open(photo))
    assert rgba.mode == "RGBA"
    a = np.asarray(rgba.getchannel("A"))

    det = FaceDetector(photo)
    det.detect()
    box = det.get_boxes()
    assert box is not None
    fx, fy, fw, fh = box
    # лицо непрозрачно
    assert a[fy + fh // 2, fx + fw // 2] > 200
    # углы прозрачны (фон)
    assert a[5, 5] < 50 and a[5, -6] < 50
    # есть и прозрачные, и непрозрачные пиксели
    assert a.min() < 50 and a.max() == 255
