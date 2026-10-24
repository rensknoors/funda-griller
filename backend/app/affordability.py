"""Affordability engine: pure arithmetic over a Buyer Profile, an asking price and one year's rules."""

from dataclasses import dataclass
from datetime import date

from app.buyer_profile import BuyerProfile, home_equity


@dataclass(frozen=True)
class Rules:
    year: int
    test_rate: float
    term_months: int
    mortgage_rate: float
    housing_ratio: tuple[tuple[int, float], ...]
    energy_label_bonus: dict[str, int]
    transfer_tax_rate: float
    starter_min_age: int
    starter_max_age: int
    starter_price_limit: int
    fixed_costs: int

    @classmethod
    def from_table(cls, year: int, table: dict) -> "Rules":
        tax = table["transfer_tax"]
        return cls(
            year=year,
            test_rate=table["test_rate"],
            term_months=table["term_months"],
            mortgage_rate=table["mortgage_rate"],
            housing_ratio=tuple((band["up_to"], band["ratio"]) for band in table["housing_ratio"]),
            energy_label_bonus=table["energy_label_bonus"],
            transfer_tax_rate=tax["rate"],
            starter_min_age=tax["starter_min_age"],
            starter_max_age=tax["starter_max_age"],
            starter_price_limit=tax["starter_price_limit"],
            fixed_costs=sum(table["fixed_costs"].values()),
        )


def _annuity_factor(annual_rate: float, months: int) -> float:
    """Principal that one euro a month repays over the term."""
    monthly_rate = annual_rate / 12
    return (1 - (1 + monthly_rate) ** -months) / monthly_rate


def _age(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _is_starter(profile: BuyerProfile, rules: Rules, today: date) -> bool:
    ages = [_age(m.birth_date, today) for m in profile.household if m.role == "adult"]
    return all(rules.starter_min_age <= age <= rules.starter_max_age for age in ages)


def _max_mortgage(income: int, energy_label: str | None, rules: Rules) -> tuple[int, int]:
    ratio = next(ratio for up_to, ratio in rules.housing_ratio if income <= up_to)
    base = int(income * ratio / 12 * _annuity_factor(rules.test_rate, rules.term_months))
    bonus = rules.energy_label_bonus.get((energy_label or "").upper(), 0)
    return base + bonus, bonus


def compute(
    profile: BuyerProfile, asking_price: int | None, energy_label: str | None, rules: Rules, today: date
) -> dict:
    starter = _is_starter(profile, rules, today)
    max_mortgage, bonus = _max_mortgage(profile.gross_annual_income, energy_label, rules)
    equity = home_equity(profile)
    own_funds = profile.assets.savings + profile.assets.investments
    budget = max_mortgage + equity + own_funds - rules.fixed_costs

    def transfer_tax(price: int) -> int:
        exempt = starter and price <= rules.starter_price_limit
        return 0 if exempt else round(price * rules.transfer_tax_rate)

    max_price = (budget / (1 + rules.transfer_tax_rate))
    if starter:
        max_price = max(max_price, min(rules.starter_price_limit, budget))
    max_price = max(0, int(max_price))

    result = {
        "max_mortgage": max_mortgage,
        "energy_label_bonus": bonus,
        "equity": equity,
        "kosten_koper": None,
        "monthly_cost": None,
        "headroom": None,
    }
    if asking_price is None:
        return result
    tax = transfer_tax(asking_price)
    needed = max(0, asking_price + tax + rules.fixed_costs - equity - own_funds)
    result["kosten_koper"] = {
        "transfer_tax": tax,
        "fixed_costs": rules.fixed_costs,
        "total": tax + rules.fixed_costs,
    }
    result["monthly_cost"] = round(needed / _annuity_factor(rules.mortgage_rate, rules.term_months))
    result["headroom"] = max_price - asking_price
    return result
