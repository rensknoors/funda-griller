"""Reads the per-year affordability rules table from disk."""

import tomllib
from pathlib import Path

from app.affordability import Rules


def load_rules(path: Path, today_year: int) -> Rules:
    """The table for `today_year`, else the latest earlier year, else the earliest one."""
    with path.open("rb") as f:
        years = {int(year): table for year, table in tomllib.load(f)["years"].items()}
    earlier = [year for year in years if year <= today_year]
    year = max(earlier) if earlier else min(years)
    return Rules.from_table(year, years[year])
