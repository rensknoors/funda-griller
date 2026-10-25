"""Verdict service (Oordeel): the only place that judges a Case (ADR-0001).

A deal-breaker Hard no is applied deterministically and never reaches the LLM client. Otherwise the
model reads the Case plus the reduced Buyer Profile, and its answer is validated here before
anything stores or shows it: one of four tiers, Flags it cites must exist, and the opening bid may
not exceed the Walk-away Maximum.

The Walk-away Maximum is not the model's: it is derived here, before the model is asked. With
sufficient comparables it is what they put the house at plus a premium; with thin or missing ones
the asking price plus a margin, stated as weakly grounded. Either way never above what the household
can afford.
"""

from collections.abc import Callable
from dataclasses import dataclass

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


@dataclass(frozen=True)
class WalkAwayMargins:
    """How far above its basis a Walk-away Maximum may sit: what sufficient comparables put the
    house at, or, when they are thin or missing, the asking price."""

    comparables_premium: float
    asking_price_margin: float


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
    margins: WalkAwayMargins,
    monthly_cost_at: Callable[[int], int | None],
) -> dict:
    """A Verdict for the Case, without id, version or creation time (the store adds those)."""
    built_from = inputs_of(case, model)
    if case["hard_no"]:
        return _hard_no(case, {**built_from, "model": None})
    if llm_client is None:
        raise LlmError("no LLM client configured")
    derivation = walk_away(case, margins)
    response = llm_client.rate(
        {**case, "provenance_legend": PROVENANCE_LEGEND, "walk_away": derivation}, reduced_profile
    )
    return {
        **_validated(response, case, derivation, monthly_cost_at),
        "deterministic": False,
        "built_from": built_from,
    }


def walk_away(case: dict, margins: WalkAwayMargins) -> dict:
    """The Walk-away Maximum and how it was derived: the lower of what the household can afford and
    its basis plus a margin. The basis is the comparables value when coverage is sufficient, else the
    asking price (weakly grounded); with neither, affordability alone (also weakly grounded)."""
    affordable = case["affordability"]["affordable_maximum"]
    comparables = case["metrics"]["asking_vs_comparables"]
    asking = _asking_price(case)
    if comparables["coverage"] == "sufficient" and comparables["comparables_value"] is not None:
        basis, margin, value = "comparables", margins.comparables_premium, comparables["comparables_value"]
    elif asking is not None:
        basis, margin, value = "asking_price", margins.asking_price_margin, asking
    else:
        basis, margin, value = "affordability", None, None
    basis_maximum = round(value * (1 + margin)) if value is not None and margin is not None else None
    binding = "basis" if basis_maximum is not None and basis_maximum < affordable else "affordability"
    return {
        "walk_away_maximum": basis_maximum if binding == "basis" else affordable,
        "basis": basis,
        "margin": margin,
        "basis_maximum": basis_maximum,
        "binding": binding,
        "weakly_grounded": basis != "comparables",
    }


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
    if (then["flag_rules_version"], then["rules_year"]) != (current["flag_rules_version"], current["rules_year"]):
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
    response: object, case: dict, derivation: dict, monthly_cost_at: Callable[[int], int | None]
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
    bid_advice, bid_problems = _bid_advice(response.get("bid_advice"), tier, case, derivation, monthly_cost_at)
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
    derivation: dict,
    monthly_cost_at: Callable[[int], int | None],
) -> tuple[dict | None, list[str]]:
    """The model supplies only the opening bid and conditions; any Walk-away Maximum it sends is
    ignored in favour of the derived one."""
    if advice is None:
        return None, ["bid_advice_missing"] if tier in BIDDING_TIERS else []
    if tier == "hard_no":
        return None, ["bid_advice_with_hard_no"]
    if not isinstance(advice, dict):
        return None, ["bid_advice_invalid"]
    opening, conditions = advice.get("opening_bid"), advice.get("conditions")
    if not _is_amount(opening):
        return None, ["bid_advice_invalid"]
    if not isinstance(conditions, list) or not all(isinstance(c, str) and c.strip() for c in conditions):
        return None, ["conditions_invalid"]
    walk_away_maximum = derivation["walk_away_maximum"]
    problems = ["opening_bid_above_walk_away_maximum"] if opening > walk_away_maximum else []
    affordability = case["affordability"]
    comparables = case["metrics"]["asking_vs_comparables"]
    return {
        "opening_bid": opening,
        "walk_away_maximum": walk_away_maximum,
        "conditions": [condition.strip() for condition in conditions],
        "affordable_maximum": affordability["affordable_maximum"],
        "comparables": {
            "coverage": comparables["coverage"],
            "count": comparables["count"],
            "comparables_value": comparables["comparables_value"],
            "maximum": derivation["basis_maximum"] if derivation["basis"] == "comparables" else None,
        },
        "derivation": {key: value for key, value in derivation.items() if key != "walk_away_maximum"},
        "asking_price": _asking_price(case),
        "monthly_cost_at_asking_price": affordability["monthly_cost"],
        "monthly_cost_at_walk_away_maximum": monthly_cost_at(walk_away_maximum),
    }, problems


def _is_amount(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
