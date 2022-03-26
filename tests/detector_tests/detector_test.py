import pytest
import typing as tp
import dataclasses
from detector.FaceDetection import FaceDetector
import os

dir_path = os.path.dirname(__file__)

@dataclasses.dataclass
class ImgPathWithBbos:
    img_path: str
    result: tp.Tuple[int, int, int, int]


TEST_CASES = [
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/christine_peterson.jpeg',
        result=(652, 231, 463, 463)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/judy_estrin.jpeg',
        result=(641, 226, 560, 560)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/tim_oreilly.jpeg',
        result=(482, 219, 573, 573)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/vint_cerf.jpeg',
        result=(562, 110, 411, 411)),
]


@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_bboxes_on_image(t: ImgPathWithBbos) -> None:
    detector = FaceDetector(t.img_path)
    detector.detect()
    assert (detector.get_boxes() == t.result).all()
