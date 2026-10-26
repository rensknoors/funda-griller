"""Reads the rule tables from disk: per-year affordability rules, the Flag rule set and the
renovation cost table."""

import tomllib
from pathlib import Path

from app.affordability import Rules
from app.flags import RuleSet
from app.renovation import CostTable


def load_rules(path: Path, today_year: int) -> Rules:
    """The table for `today_year`, else the latest earlier year, else the earliest one."""
    with path.open("rb") as f:
        years = {int(year): table for year, table in tomllib.load(f)["years"].items()}
    earlier = [year for year in years if year <= today_year]
    year = max(earlier) if earlier else min(years)
    return Rules.from_table(year, years[year])


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
