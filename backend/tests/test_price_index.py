"""Bringing a WOZ value from its peildatum to today with the CBS price index (pure)."""

from datetime import date

import pytest

from app.price_index import PriceIndex, peildatum

INDEX = PriceIndex(
    version=1,
    source="test",
    months={"2024-01": 130.5, "2025-01": 145.5, "2026-08": 156.6, "2026-09": 156.0},
)


def test_a_woz_value_is_brought_to_the_latest_published_month():
    indexed = INDEX.bring_to(400_000, date(2025, 1, 1), date(2026, 10, 24))

    # 400.000 × 156,0 / 145,5
    assert (indexed.value, indexed.index_from, indexed.index_to) == (428_866, "2025-01", "2026-09")


def test_a_month_not_yet_published_falls_back_to_the_latest_before_it():
    indexed = INDEX.bring_to(400_000, date(2025, 1, 1), date(2026, 9, 3))

    assert indexed.index_to == "2026-09"
    assert INDEX.bring_to(400_000, date(2025, 1, 1), date(2026, 8, 31)).index_to == "2026-08"


def test_a_peildatum_outside_the_series_cannot_be_indexed():
    assert INDEX.bring_to(400_000, date(2019, 1, 1), date(2026, 10, 24)) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2025-01-01", date(2025, 1, 1)), ("1 jan 2025", date(2025, 1, 1)), ("1 januari 2024", date(2024, 1, 1)), ("31 dec 2023", date(2023, 12, 31))],
)
def test_woz_dates_are_read_in_both_notations(text, expected):
    assert peildatum(text) == expected


@pytest.mark.parametrize("text", [None, "", "ergens in 2025", "1 foo 2025"])
def test_an_unreadable_woz_date_is_none(text):
    assert peildatum(text) is None
