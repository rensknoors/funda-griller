"""The price index of existing owner-occupied homes, to bring a WOZ value from its peildatum to today.
Pure: the table is read from config by the rules loader."""

import re
from dataclasses import dataclass
from datetime import date

_MONTHS = {
    "jan": 1, "feb": 2, "mrt": 3, "maa": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}
_DUTCH_DATE = re.compile(r"^\s*(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})\s*$")


def peildatum(text: object) -> date | None:
    """A WOZ value's date, as ISO ("2025-01-01") or as the provider writes it ("1 jan 2025")."""
    if not isinstance(text, str):
        return None
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        pass
    match = _DUTCH_DATE.match(text.casefold())
    month = _MONTHS.get(match.group(2)[:3]) if match else None
    if match is None or month is None:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None


@dataclass(frozen=True)
class Indexed:
    value: int
    index_from: str
    index_to: str


@dataclass(frozen=True)
class PriceIndex:
    version: int
    source: str
    # "YYYY-MM" to the index figure for that month.
    months: dict[str, float]

    def bring_to(self, value: int, since: date, today: date) -> Indexed | None:
        """`value` at `since` in today's prices: × index(latest published month up to today) /
        index(the month of `since`). None when `since` falls outside the series."""
        start = f"{since.year:04d}-{since.month:02d}"
        published = [month for month in self.months if month <= f"{today.year:04d}-{today.month:02d}"]
        if start not in self.months or not published:
            return None
        end = max(published)
        return Indexed(round(value * self.months[end] / self.months[start]), start, end)
