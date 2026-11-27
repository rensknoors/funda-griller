"""House types: funda's object type and soort woning read into the categories the NVM market
figures use, and the average overbid per category. Pure."""

from dataclasses import dataclass

# Words in funda's soort woning that mark an apartment.
_APARTMENT_WORDS = (
    "appartement", "bovenwoning", "benedenwoning", "flat", "maisonnette", "penthouse",
    "portiek", "galerij", "dubbel benedenhuis", "tussenverdieping",
)
# First match wins; "halfvrijstaand" before "vrijstaand".
_HOUSE_CATEGORIES = (
    ("tussenwoning", "tussenwoning"),
    ("hoekwoning", "hoekwoning"),
    ("eindwoning", "hoekwoning"),
    ("2-onder-1-kap", "twee_onder_een_kap"),
    ("twee-onder-een-kap", "twee_onder_een_kap"),
    ("halfvrijstaand", "twee_onder_een_kap"),
    ("vrijstaand", "vrijstaand"),
)

# Dutch UI labels.
LABELS = {
    "appartement": "appartement",
    "tussenwoning": "tussenwoning",
    "hoekwoning": "hoekwoning",
    "twee_onder_een_kap": "twee-onder-een-kapwoning",
    "vrijstaand": "vrijstaande woning",
}


def kind(object_type: str | None, house_type: str | None) -> str | None:
    """"apartment" or "house", from funda's object type, else from the soort woning."""
    if object_type in ("apartment", "house"):
        return object_type
    if object_type is not None or not house_type:
        return None
    text = house_type.casefold()
    return "apartment" if any(word in text for word in _APARTMENT_WORDS) else "house"


def category(object_type: str | None, house_type: str | None) -> str | None:
    """appartement, tussenwoning, hoekwoning, twee_onder_een_kap or vrijstaand; None when the soort
    woning names none of them (e.g. a geschakelde woning)."""
    found = kind(object_type, house_type)
    if found == "apartment":
        return "appartement"
    if found != "house" or not house_type:
        return None
    text = house_type.casefold()
    return next((name for word, name in _HOUSE_CATEGORIES if word in text), None)


@dataclass(frozen=True)
class AskingPriceMargins:
    """Average overbid by category, from a dated market source (config/bid_margins.toml)."""

    version: int
    source: str
    period: str
    # Category to share above the asking price; "all" for an unknown soort woning.
    average_overbid: dict[str, float]

    def for_category(self, house_category: str | None) -> dict:
        known = house_category in self.average_overbid and house_category != "all"
        return {
            "value": self.average_overbid[house_category if known else "all"],
            "house_type": house_category if known else None,
            "source": self.source,
            "period": self.period,
        }
