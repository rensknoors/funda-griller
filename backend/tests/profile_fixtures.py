"""Buyer Profiles for three household shapes."""

import copy

_BASE = {
    "household": [{"role": "adult", "birth_date": "1988-04-12"}],
    "gross_annual_income": 95_000,
    "assets": {"savings": 40_000, "investments": 15_000},
    "must_haves": [],
    "nice_to_haves": [],
    "deal_breakers": [],
    "commute_destinations": [],
    "renovation_tolerance": 3,
}


def typical_profile() -> dict:
    """Two adults and a child, one income, a home with modest equity."""
    return {
        **copy.deepcopy(_BASE),
        "household": [
            {"role": "adult", "birth_date": "1988-04-12"},
            {"role": "adult", "birth_date": "1990-09-30"},
            {"role": "child", "birth_date": "2020-01-15"},
        ],
        "current_home": {"value": 400_000, "outstanding_mortgage": 220_000, "selling_costs": 8_000},
    }


def low_income_profile() -> dict:
    """Two adults in their twenties, renting, little saved."""
    return {
        **copy.deepcopy(_BASE),
        "household": [
            {"role": "adult", "birth_date": "2000-02-01"},
            {"role": "adult", "birth_date": "1999-06-15"},
        ],
        "gross_annual_income": 42_000,
        "assets": {"savings": 12_000, "investments": 0},
    }


def high_equity_profile() -> dict:
    """Older couple selling a nearly paid-off home."""
    return {
        **copy.deepcopy(_BASE),
        "household": [
            {"role": "adult", "birth_date": "1970-03-03"},
            {"role": "adult", "birth_date": "1972-11-20"},
        ],
        "gross_annual_income": 60_000,
        "assets": {"savings": 50_000, "investments": 100_000},
        "current_home": {"value": 900_000, "outstanding_mortgage": 100_000, "selling_costs": 20_000},
    }
