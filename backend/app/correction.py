"""Corrections (Correcties): the household's own value for a Listing fact the Case computes with.
What may be corrected, which values are plausible, and how a Correction is applied to a snapshot.
Pure."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.flags import ENERGY_LABELS
from app.house_type import recognised

# The Listing facts the Case computes with, which the household may correct (spec decision 2).
CORRECTABLE_FACTS = (
    "living_area",
    "plot_area",
    "rooms",
    "bedrooms",
    "construction_year",
    "house_type",
    "energy_label",
    "ownership_situation",
)
_WHOLE_NUMBERS = ("living_area", "plot_area", "rooms", "bedrooms", "construction_year")
# The oldest build year accepted; Dutch houses from before then are not on funda.
_OLDEST_BUILD_YEAR = 1100
# How far ahead a new-build's build year may lie.
_BUILD_YEARS_AHEAD = 5


@dataclass(frozen=True)
class Correction:
    """One live Correction. `listing_value_at_correction` is the Listing's value when it was made
    (or last kept), so a re-capture can tell whether the Listing has moved since."""

    key: str
    value: str | int
    explanation: str
    created_at: str
    listing_value_at_correction: object


class NotCorrectable(ValueError):
    """The key is no Listing fact the Case computes with."""


def corrected_value(key: str, value: object, today: date) -> str | int:
    """The Correction's value as the Case uses it (an energielabel in capitals, text trimmed).
    Raises NotCorrectable for any other key and ValueError for an implausible value: areas, rooms
    and bedrooms are positive whole numbers, a build year lies between 1100 and five years from
    `today`, the energielabel is a known one and the soort woning one funda uses."""
    if key not in CORRECTABLE_FACTS:
        raise NotCorrectable(key)
    if key in _WHOLE_NUMBERS:
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(key)
        if key == "construction_year" and not _OLDEST_BUILD_YEAR <= value <= today.year + _BUILD_YEARS_AHEAD:
            raise ValueError(key)
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(key)
    text = value.strip()
    if key == "energy_label":
        if text.upper() not in ENERGY_LABELS:
            raise ValueError(key)
        return text.upper()
    if key == "house_type" and not recognised(text):
        raise ValueError(key)
    return text


def applied(snapshot: dict, corrections: Sequence[Correction]) -> dict:
    """The snapshot with each Correction in place of the Listing's value. A corrected soort woning
    also decides the kind (house or apartment), so funda's object type gives way to it."""
    result = {**snapshot, **{c.key: c.value for c in corrections}}
    if any(c.key == "house_type" for c in corrections):
        result["object_type"] = None
    return result
