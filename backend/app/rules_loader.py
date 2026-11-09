"""Reads the rule tables from disk: per-year affordability rules, the Flag rule set, the
renovation cost table and the house price index."""

import tomllib
from datetime import date
from pathlib import Path

from app.affordability import Rules
from app.flags import RuleSet
from app.house_type import AskingPriceMargins
from app.price_index import PriceIndex
from app.renovation import CostTable


def expected_levering(today: date, months: int) -> date:
    """When a bid made today is expected to transfer at the notary: `months` on, same day (or the
    month's last day)."""
    month_index = today.month - 1 + months
    year, month = today.year + month_index // 12, month_index % 12 + 1
    for day in range(today.day, 0, -1):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise AssertionError("unreachable")


def load_rules(path: Path, levering_year: int) -> Rules:
    """The table for `levering_year`, else the latest earlier year, else the earliest one."""
    with path.open("rb") as f:
        data = tomllib.load(f)
    years = {int(year): table for year, table in data["years"].items()}
    earlier = [year for year in years if year <= levering_year]
    year = max(earlier) if earlier else min(years)
    return Rules.from_table(data["version"], year, years[year], data["market_rate"])


def load_price_index(path: Path) -> PriceIndex:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return PriceIndex(version=data["version"], source=data["source"], months=dict(data["months"]))


def load_bid_margins(path: Path) -> AskingPriceMargins:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return AskingPriceMargins(data["version"], data["source"], data["period"], dict(data["average_overbid"]))


def load_flag_rules(path: Path) -> RuleSet:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return RuleSet(
        version=data["version"],
        rules=tuple(data.get("rules", ())),
        features=tuple(data.get("features", ())),
    )


def load_cost_table(path: Path) -> CostTable:
    with path.open("rb") as f:
        data = tomllib.load(f)
    low_band, high_band = data["size_bands"]
    return CostTable(
        version=data["version"],
        size_bands=(low_band, high_band),
        assumed_living_area=data["assumed_living_area"],
        items=tuple(data.get("items", ())),
    )
