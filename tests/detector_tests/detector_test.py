import dataclasses
import os
import typing as tp

import pytest

from detector.FaceDetection import FaceDetector

dir_path = os.path.dirname(__file__)


@dataclasses.dataclass
class ImgPathWithBbos:
    img_path: str
    yunet: tp.Tuple[int, int, int, int]
    cascade: tp.Tuple[int, int, int, int]


# Ожидания для YuNet и для каскада Хаара (запасной движок).
# Допуск ±20 px: значения могут немного отличаться между версиями OpenCV.
TEST_CASES = [
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/photos/кристин_петерсон.jpeg',
        yunet=(700, 245, 333, 432),
        cascade=(652, 231, 463, 463)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/photos/judy_estrin.jpeg',
        yunet=(649, 181, 493, 572),
        cascade=(641, 226, 560, 560)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/photos/tim_oreilly.jpeg',
        yunet=(570, 264, 425, 517),
        cascade=(482, 219, 573, 573)),
    ImgPathWithBbos(
        img_path=f'{dir_path}/../assets/photos/vint_cerf.jpeg',
        yunet=(610, 121, 287, 381),
        cascade=(562, 110, 411, 411)),
]

TOLERANCE = 20


@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_bboxes_on_image(t: ImgPathWithBbos) -> None:
    detector = FaceDetector(t.img_path)
    detector.detect()
    expected = t.yunet if detector.engine() == "yunet" else t.cascade
    box = detector.get_boxes()
    assert box is not None
    for actual, exp in zip(box, expected):
        assert abs(actual - exp) <= TOLERANCE
    assert detector.has_faces()


@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_landmarks_with_yunet(t: ImgPathWithBbos) -> None:
    detector = FaceDetector(t.img_path)
    detector.detect()
    if detector.engine() != "yunet":
        pytest.skip("YuNet недоступен — пропускаем проверку ключевых точек")
    landmarks = detector.get_landmarks()
    assert landmarks is not None
    assert len(landmarks) == 5
    h, w = detector.img.shape[:2]
    for (lx, ly) in landmarks:
        assert 0 <= lx <= w
        assert 0 <= ly <= h
    # середина отрезка между глазами внутри рамки лица
    eye_center = detector.get_eye_center()
    assert eye_center is not None
    x, y, bw, bh = detector.get_boxes()
    assert x <= eye_center[0] <= x + bw
    assert y <= eye_center[1] <= y + bh
