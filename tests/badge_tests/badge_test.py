import pytest
import typing as tp
import dataclasses
from badge_generator.BadgeGenerator import Badge
import os

dir_path = os.path.dirname(__file__)
@dataclasses.dataclass
class BadgeChecker:
    file_path: str
    template_path: str

    name: str
    surname: str
    photo_coords: (int, int)

TEST_CASES = [
    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/кристин_петерсон.jpeg',
        template_path=f'{dir_path}/../assets/1отряд.png',
        name='Петерсон',
        surname='Кристин',
        photo_coords=(154, 0)),

    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/judy_estrin.jpeg',
        template_path=f'{dir_path}/../assets/1отряд.png',
        name='Estrin',
        surname='Judy',
        photo_coords=(109, 0)),

    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/tim_oreilly.jpeg',
        template_path=f'{dir_path}/../assets/1отряд.png',
        name='Oreilly',
        surname='Tim',
        photo_coords=(58, 0)),

    BadgeChecker(
        file_path=f'{dir_path}/../assets/photos/vint_cerf.jpeg',
        template_path=f'{dir_path}/../assets/1отряд.png',
        name='Cerf',
        surname='Vint',
        photo_coords=(147, 0))
]

@pytest.mark.parametrize("t", TEST_CASES, ids=str)
def test_badge_init(t: BadgeChecker) -> None:
    badge = Badge(0, t.file_path, t.template_path)
    assert (badge.get_name() == t.name)
    assert (badge.get_surname() == t.surname)
    assert (badge.get_photo_coords() == t.photo_coords)