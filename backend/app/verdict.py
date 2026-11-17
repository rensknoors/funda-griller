"""Verdict service (Oordeel): the only place that judges a Case (ADR-0001).

A deal-breaker Hard no is applied deterministically and never reaches the LLM client. Otherwise the
model reads the Case plus the reduced Buyer Profile, and its answer is validated here before
anything stores or shows it: one of four tiers, Flags it cites must exist, and the opening bid may
not exceed the Walk-away Maximum.

The Walk-away Maximum is not the model's: it is derived here, before the model is asked. With
the Expected Sale Price, less the Renovation Estimate's Direct nodig midpoint, plus a premium, never
above what the household can afford; without an Expected Sale Price there is none. Must buy needs an
Expected Sale Price, and an opening bid needs a Walk-away Maximum.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypedDict

from app.ports import LlmClient, LlmError

TIERS = ("must_buy", "consider", "skip", "hard_no")
# Tiers that tell the household to bid, so they need Bid Advice.
BIDDING_TIERS = ("must_buy", "consider")

# Sent with every Case so the model can weigh a seller's claim below an official register.
PROVENANCE_LEGEND = {
    "listing": "Stated in the funda Listing by the selling agent; not verified.",
    "source:official": "From an official register; the most reliable class.",
    "source:third_party": "From a third-party service, not an official register; indicative only.",
    "observation": "Estimated by a vision model from Listing photos; may be wrong.",
    "finding": "Stated by the seller in a Document; seller-stated, not verified.",
    "computed": "Arithmetic over other facts and the household's derived figures.",
    "buyer_profile": "The household's own preferences.",
    "rule": "A threshold from the versioned Flag rule set.",
}


class WalkAwayDerivation(TypedDict):
    """The derived Walk-away Maximum and how: its basis (the Expected Sale Price), the Direct nodig
    renovation cost taken off it, the premium over the rest and what that came to, which of basis
    and affordability bound it, and whether it is weakly grounded. Without an Expected Sale Price
    there is no maximum and everything else but the renovation cost is None."""

    walk_away_maximum: int | None
    basis: Literal["expected_sale_price"] | None
    renovation_direct: int
    margin: float | None
    basis_maximum: int | None
    binding: Literal["basis", "affordability"] | None
    weakly_grounded: bool | None


@dataclass(frozen=True)
class GuideBidConfig:
    """The Guide Bid's configured figures (config/defaults.toml, `[guide_bid]`): the discount per
    Prijsstelling, the extra discount for time on the market (over the long threshold, or the very
    long one instead) and for a price reduction, the cap on the total, the band the model's opening
    bid must stay within, and the rounding step."""

    discount_hoog_ingezet: float
    discount_marktconform: float
    discount_laag_ingezet: float
    band: float
    rounding_step: int
    long_on_market_days: int
    discount_long_on_market: float
    very_long_on_market_days: int
    discount_very_long_on_market: float
    discount_price_reduction: float
    max_discount: float

    def discount_for(self, prijsstelling: str) -> float:
        return {
            "hoog ingezet": self.discount_hoog_ingezet,
            "laag ingezet": self.discount_laag_ingezet,
        }.get(prijsstelling, self.discount_marktconform)

    def discount_for_days(self, days: int) -> float:
        if days > self.very_long_on_market_days:
            return self.discount_very_long_on_market
        if days > self.long_on_market_days:
            return self.discount_long_on_market
        return 0.0


class GuideBid(TypedDict):
    """The Guide Bid and how it came about. `breakdown` holds one entry per discount component
    (Prijsstelling, and with a price history days on the market and the price reduction), each with
    its label and discount; `discount` is their total, capped (`discount_capped`). `tempo_known` is
    false without a price history, so the tempo did not count. `capped_by` names the cap that lowered
    the value, if any."""

    value: int
    discount: float
    discount_capped: bool
    breakdown: dict[str, dict]
    tempo_known: bool
    weakly_grounded: bool
    capped_by: Literal["asking_price", "walk_away_maximum"] | None
    band: float


class MonthlyCosts(TypedDict):
    """Monthly cost of the mortgage needed at a price: gross, and net of hypotheekrenteaftrek."""

    gross: int | None
    net: int | None


class InvalidVerdict(Exception):
    """The model's answer broke the Verdict contract; it is reported, never stored or shown."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(", ".join(problems))
        self.problems = problems


def judge(
    case: dict,
    reduced_profile: dict,
    llm_client: LlmClient | None,
    model: str | None,
    walk_away_premium: float,
    monthly_cost_at: Callable[[int], MonthlyCosts],
    guide_bid_config: GuideBidConfig,
) -> dict:
    """A Verdict for the Case, without id, version or creation time (the store adds those)."""
    built_from = inputs_of(case, model)
    if case["hard_no"]:
        return _hard_no(case, {**built_from, "model": None})
    if llm_client is None:
        raise LlmError("no LLM client configured")
    derivation = derive_walk_away_maximum(case, walk_away_premium)
    maximum = derivation["walk_away_maximum"]
    walk_away = {**derivation, "monthly_cost": monthly_cost_at(maximum) if maximum is not None else None}
    guide_bid = derive_guide_bid(case, maximum, guide_bid_config)
    response = llm_client.rate(
        {
            **_for_llm(case),
            "provenance_legend": PROVENANCE_LEGEND,
            "walk_away": walk_away,
            "guide_bid": guide_bid,
        },
        reduced_profile,
    )
    return {
        **_validated(response, case, derivation, monthly_cost_at, guide_bid),
        "deterministic": False,
        "built_from": built_from,
    }


def _for_llm(case: dict) -> dict:
    """The Case as the LLM may see it: without the household's debts, which only the app's own UI
    shows (ticket 30)."""
    affordability = case["affordability"]
    if not affordability:
        return case
    return {**case, "affordability": {key: value for key, value in affordability.items() if key != "debts"}}


def derive_walk_away_maximum(case: dict, premium: float) -> WalkAwayDerivation:
    """The Walk-away Maximum and how it was derived: the lower of what the household can afford and
    the Expected Sale Price less the Direct nodig renovation cost plus the premium. Without an
    Expected Sale Price there is none."""
    renovation_direct = case["renovation_estimate"]["direct_midpoint"]
    expected = case["metrics"]["expected_sale_price"]
    if expected["value"] is None:
        return {
            "walk_away_maximum": None,
            "basis": None,
            "renovation_direct": renovation_direct,
            "margin": None,
            "basis_maximum": None,
            "binding": None,
            "weakly_grounded": None,
        }
    affordable = case["affordability"]["affordable_maximum"]
    basis_maximum = round((expected["value"] - renovation_direct) * (1 + premium))
    binding: Literal["basis", "affordability"] = "basis" if basis_maximum < affordable else "affordability"
    return {
        "walk_away_maximum": basis_maximum if binding == "basis" else affordable,
        "basis": "expected_sale_price",
        "renovation_direct": renovation_direct,
        "margin": premium,
        "basis_maximum": basis_maximum,
        "binding": binding,
        "weakly_grounded": expected["weakly_grounded"],
    }


def derive_guide_bid(case: dict, walk_away_maximum: int | None, config: GuideBidConfig) -> GuideBid | None:
    """The opening bid the Case derives before the model sees it: the Expected Sale Price less the
    discount for the Prijsstelling and the time on the market (capped), never above the asking price
    or the Walk-away Maximum, rounded down to the step. None without a Walk-away Maximum, an Expected
    Sale Price or an asking price (so no Prijsstelling), and for a house sold under reservation."""
    if walk_away_maximum is None or case["sold_under_reservation"]:
        return None
    expected = case["metrics"]["expected_sale_price"]
    prijsstelling = case["metrics"]["asking_vs_expected"]
    if expected["value"] is None or prijsstelling is None:
        return None
    tempo = case["metrics"].get("market_tempo")
    breakdown: dict[str, dict] = {
        "prijsstelling": {
            "label": prijsstelling["prijsstelling"],
            "discount": config.discount_for(prijsstelling["prijsstelling"]),
        },
        **(_tempo_components(tempo, config) if tempo else {}),
    }
    total = sum(component["discount"] for component in breakdown.values())
    discount = round(min(total, config.max_discount), 4)
    value = round(expected["value"] * (1 - discount))
    capped_by: Literal["asking_price", "walk_away_maximum"] | None = None
    if prijsstelling["asking_price"] < value:
        value, capped_by = prijsstelling["asking_price"], "asking_price"
    if walk_away_maximum < value:
        value, capped_by = walk_away_maximum, "walk_away_maximum"
    return {
        "value": math.floor(value / config.rounding_step) * config.rounding_step,
        "discount": discount,
        "discount_capped": total > config.max_discount,
        "breakdown": breakdown,
        "tempo_known": tempo is not None,
        "weakly_grounded": expected["weakly_grounded"],
        "capped_by": capped_by,
        "band": config.band,
    }


def _tempo_components(tempo: dict, config: GuideBidConfig) -> dict[str, dict]:
    """The Guide Bid's discount for time on the market and for a price reduction (Case metric
    `market_tempo`), labelled for the Biedadvies."""
    days = tempo["days_on_market"]
    first, asking = tempo["first_asking_price"], tempo["asking_price"]
    return {
        "days_on_market": {"label": f"{days} dagen", "days": days, "discount": config.discount_for_days(days)},
        "price_reduction": {
            "label": f"van {_euro(first)} naar {_euro(asking)}" if tempo["price_reduction"] else "geen",
            "first_asking_price": first,
            "asking_price": asking,
            "discount": config.discount_price_reduction if tempo["price_reduction"] else 0.0,
        },
    }


def _euro(amount: int) -> str:
    return f"€ {amount:,}".replace(",", ".")


def _asking_price(case: dict) -> int | None:
    return next(
        (f["value"] for f in case["facts"] if f["provenance"] == "listing" and f["key"] == "asking_price"),
        None,
    )


def inputs_of(case: dict, model: str | None) -> dict:
    """What a Verdict on this Case depends on; a Verdict is out of date when any of it changes."""
    source_fetches: dict[str, str] = {}
    for fact in case["facts"]:
        if fact["provenance"] == "source":
            source_fetches[fact["source"]] = max(fact["fetched_at"], source_fetches.get(fact["source"], ""))
    return {
        **case["built_from"],
        "rules_year": case["rules"]["year"],
        "rules_version": case["rules"].get("version"),
        # The rate per loan route the figures rest on; a change shows through the profile or
        # rules version, so it is recorded, not compared.
        "mortgage_rates": case["rules"].get("rates"),
        "source_fetches": source_fetches,
        "model": model,
    }


def changed_inputs(verdict: dict, current: dict) -> list[str]:
    """Which inputs moved since the Verdict was made: `case`, `buyer_profile`, `rules`, `model`."""
    then = verdict["built_from"]
    changed = []
    if (
        then["snapshot_id"] != current["snapshot_id"]
        or then["source_fetches"] != current["source_fetches"]
        or then.get("observation_run") != current.get("observation_run")
        or then.get("documents", []) != current.get("documents", [])
    ):
        changed.append("case")
    if then["profile_version"] != current["profile_version"]:
        changed.append("buyer_profile")
    if (
        then["flag_rules_version"],
        then["rules_year"],
        then.get("rules_version"),
        then.get("cost_table_version"),
        then.get("price_index_version"),
        then.get("bid_margins_version"),
    ) != (
        current["flag_rules_version"],
        current["rules_year"],
        current.get("rules_version"),
        current.get("cost_table_version"),
        current.get("price_index_version"),
        current.get("bid_margins_version"),
    ):
        changed.append("rules")
    if not verdict["deterministic"] and then["model"] != current["model"]:
        changed.append("model")
    return changed


def _hard_no(case: dict, built_from: dict) -> dict:
    hard_no = case["hard_no"]
    flag = next(f for f in case["flags"] if f["id"] == hard_no["flag_id"])
    return {
        "tier": "hard_no",
        "summary": f"Deal-breaker geraakt: {hard_no['deal_breaker']}.",
        "reasoning": f"{flag['title']}. Dit raakt je deal-breaker ‘{hard_no['deal_breaker']}’.",
        "deal_breaker": hard_no["deal_breaker"],
        "cited_flags": [_cited(flag)],
        "bid_advice": None,
        "deterministic": True,
        "built_from": built_from,
    }


def _cited(flag: dict) -> dict:
    return {"id": flag["id"], "title": flag["title"], "class": flag["class"]}


def _validated(
    response: object,
    case: dict,
    derivation: WalkAwayDerivation,
    monthly_cost_at: Callable[[int], MonthlyCosts],
    guide_bid: GuideBid | None,
) -> dict:
    if not isinstance(response, dict):
        raise InvalidVerdict(["not_an_object"])
    problems = []
    tier = response.get("tier")
    if tier not in TIERS:
        problems.append("tier_invalid")
    summary, reasoning = response.get("summary"), response.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        problems.append("reasoning_missing")
    if summary is not None and not isinstance(summary, str):
        problems.append("summary_invalid")
    flags = {flag["id"]: flag for flag in case["flags"]}
    cited_ids = response.get("cited_flags") or []
    if not isinstance(cited_ids, list) or any(flag_id not in flags for flag_id in cited_ids):
        problems.append("unknown_flag_cited")
        cited_ids = []
    if tier == "must_buy" and case["metrics"]["expected_sale_price"]["value"] is None:
        problems.append("must_buy_without_expected_sale_price")
    bid_advice, bid_problems = _bid_advice(
        response.get("bid_advice"), tier, case, derivation, monthly_cost_at, guide_bid
    )
    problems += bid_problems
    if problems:
        raise InvalidVerdict(problems)
    return {
        "tier": tier,
        "summary": (summary or "").strip(),
        "reasoning": reasoning.strip(),
        "deal_breaker": None,
        "cited_flags": [_cited(flags[flag_id]) for flag_id in dict.fromkeys(cited_ids)],
        "bid_advice": bid_advice,
    }


def _bid_advice(
    advice: object,
    tier: object,
    case: dict,
    derivation: WalkAwayDerivation,
    monthly_cost_at: Callable[[int], MonthlyCosts],
    guide_bid: GuideBid | None,
) -> tuple[dict | None, list[str]]:
    """The model supplies only the opening bid, conditions and, when it leaves the Guide Bid, its
    reason; any Walk-away Maximum it sends is ignored in favour of the derived one."""
    if advice is None:
        return None, ["bid_advice_missing"] if tier in BIDDING_TIERS else []
    if tier == "hard_no":
        return None, ["bid_advice_with_hard_no"]
    if not isinstance(advice, dict):
        return None, ["bid_advice_invalid"]
    opening, conditions = advice.get("opening_bid"), advice.get("conditions")
    walk_away_maximum = derivation["walk_away_maximum"]
    if walk_away_maximum is None or case["sold_under_reservation"]:
        return _conditions_only(opening, conditions, case)
    if not _is_amount(opening):
        return None, ["bid_advice_invalid"]
    if not isinstance(conditions, list) or not all(isinstance(c, str) and c.strip() for c in conditions):
        return None, ["conditions_invalid"]
    problems = ["opening_bid_above_walk_away_maximum"] if opening > walk_away_maximum else []
    if guide_bid is not None and abs(opening - guide_bid["value"]) > guide_bid["value"] * guide_bid["band"]:
        problems.append("opening_bid_outside_guide_bid_band")
    reason = advice.get("deviation_reason")
    deviates = guide_bid is not None and opening != guide_bid["value"]
    affordability = case["affordability"]
    comparables = case["metrics"]["asking_vs_comparables"]
    at_walk_away = monthly_cost_at(walk_away_maximum)
    return {
        "opening_bid": opening,
        "walk_away_maximum": walk_away_maximum,
        "conditions": [condition.strip() for condition in conditions],
        "affordable_maximum": affordability["affordable_maximum"],
        "comparables": {
            "coverage": comparables["coverage"],
            "count": comparables["count"],
            "comparables_value": comparables["comparables_value"],
            "maximum": None,
        },
        "derivation": {key: value for key, value in derivation.items() if key != "walk_away_maximum"},
        "guide_bid": guide_bid,
        "guide_bid_deviation_reason": reason.strip() if deviates and isinstance(reason, str) and reason.strip() else None,
        "sold_under_reservation": False,
        "asking_price": _asking_price(case),
        "expected_sale_price": case["metrics"]["expected_sale_price"]["value"],
        "monthly_cost_at_expected_sale_price": affordability["monthly_cost"],
        "monthly_cost_net_at_expected_sale_price": affordability["monthly_cost_net"],
        "monthly_cost_at_walk_away_maximum": at_walk_away["gross"],
        "monthly_cost_net_at_walk_away_maximum": at_walk_away["net"],
    }, problems


def _conditions_only(opening: object, conditions: object, case: dict) -> tuple[dict | None, list[str]]:
    """Bid Advice without an Expected Sale Price: no Walk-away Maximum, so no opening bid either."""
    reserved = case["sold_under_reservation"]
    if opening is not None:
        return None, ["opening_bid_when_sold_under_reservation" if reserved else "opening_bid_without_walk_away_maximum"]
    if not isinstance(conditions, list) or not all(isinstance(c, str) and c.strip() for c in conditions):
        return None, ["conditions_invalid"]
    return {
        "opening_bid": None,
        "walk_away_maximum": None,
        "conditions": [condition.strip() for condition in conditions],
        "affordable_maximum": case["affordability"]["affordable_maximum"],
        "guide_bid": None,
        "sold_under_reservation": reserved,
        "asking_price": _asking_price(case),
        "expected_sale_price": None,
        "monthly_cost_at_expected_sale_price": None,
        "monthly_cost_net_at_expected_sale_price": None,
        "monthly_cost_at_walk_away_maximum": None,
        "monthly_cost_net_at_walk_away_maximum": None,
    }, []


def _is_amount(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
