import pytest
import typing as tp

from .

@dataclasses.dataclass
class ImgPathWithBbos:
    img_path: str
    result: tp.Tuple[int]

TEST_CASES = [
    ImgPathWithBbos(
        img_path='andrey.jepg', 
        result=(302, 265, 112, 112)),
    ImgPathWithBbos(
        img_path='maria.jpeg',
        result=(647, 673, 234, 234)),
    ImgPathWithBbos(
        img_path='kate.jpg',
        result=(185, 228, 107, 107)),
    ImgPathWithBbos(
        img_path='ruslan.jpg',
        result=(190, 292, 235, 235)),
]

@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_without_random(t: ImgPathWithBbos) -> None:
    detector = FaceDetector(t.img_path)
    detector.detect()
    assert detector.get_boxes() == t.results[i]