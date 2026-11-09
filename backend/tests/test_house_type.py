"""Reading funda's object type and soort woning into the categories the market figures use (pure)."""

import pytest

from app.house_type import category, kind


@pytest.mark.parametrize(
    ("object_type", "house_type", "expected"),
    [
        ("apartment", "Bovenwoning", "appartement"),
        (None, "Portiekflat", "appartement"),
        ("house", "Eengezinswoning, tussenwoning", "tussenwoning"),
        ("house", "Eengezinswoning, hoekwoning", "hoekwoning"),
        ("house", "Eengezinswoning, eindwoning", "hoekwoning"),
        ("house", "Woonboerderij, 2-onder-1-kapwoning", "twee_onder_een_kap"),
        ("house", "Eengezinswoning, halfvrijstaande woning", "twee_onder_een_kap"),
        ("house", "Villa, vrijstaande woning", "vrijstaand"),
        ("house", "Eengezinswoning, geschakelde woning", None),
        ("house", None, None),
        (None, None, None),
    ],
)
def test_category(object_type, house_type, expected):
    assert category(object_type, house_type) == expected


@pytest.mark.parametrize(
    ("object_type", "house_type", "expected"),
    [
        ("apartment", None, "apartment"),
        ("house", "Villa, vrijstaande woning", "house"),
        (None, "Bovenwoning", "apartment"),
        (None, "Eengezinswoning, tussenwoning", "house"),
        (None, None, None),
        ("parking", None, None),
    ],
)
def test_kind_is_apartment_or_house(object_type, house_type, expected):
    assert kind(object_type, house_type) == expected
