"""Verdict service (Oordeel): the only place that judges a Case (ADR-0001).

A deal-breaker Hard no is applied deterministically and never reaches the LLM client. Otherwise the
model reads the Case plus the reduced Buyer Profile, and its answer is validated here before
anything stores or shows it: one of four tiers, Flags it cites must exist, and the Walk-away Maximum
may not exceed what the household can afford.
"""

from collections.abc import Callable

from app.ports import LlmClient

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


class InvalidVerdict(Exception):
    """The model's answer broke the Verdict contract; it is reported, never stored or shown."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__(", ".join(problems))
        self.problems = problems


def judge(
    case: dict,
    reduced_profile: dict,
    llm_client: LlmClient,
    model: str | None,
    monthly_cost_at: Callable[[int], int | None],
) -> dict:
    """A Verdict for the Case, without id, version or creation time (the store adds those)."""
    built_from = inputs_of(case, model)
    if case["hard_no"]:
        return _hard_no(case, {**built_from, "model": None})
    response = llm_client.rate({**case, "provenance_legend": PROVENANCE_LEGEND}, reduced_profile)
    return {**_validated(response, case, monthly_cost_at), "deterministic": False, "built_from": built_from}


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


def _validated(response: object, case: dict, monthly_cost_at: Callable[[int], int | None]) -> dict:
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
    bid_advice, bid_problems = _bid_advice(response.get("bid_advice"), tier, case, monthly_cost_at)
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
    advice: object, tier: object, case: dict, monthly_cost_at: Callable[[int], int | None]
) -> tuple[dict | None, list[str]]:
    if advice is None:
        return None, ["bid_advice_missing"] if tier in BIDDING_TIERS else []
    if tier == "hard_no":
        return None, ["bid_advice_with_hard_no"]
    if not isinstance(advice, dict):
        return None, ["bid_advice_invalid"]
    opening, walk_away, conditions = (
        advice.get("opening_bid"),
        advice.get("walk_away_maximum"),
        advice.get("conditions"),
    )
    if not all(_is_amount(amount) for amount in (opening, walk_away)):
        return None, ["bid_advice_invalid"]
    if not isinstance(conditions, list) or not all(isinstance(c, str) and c.strip() for c in conditions):
        return None, ["conditions_invalid"]
    affordability = case["affordability"]
    problems = []
    if opening > walk_away:
        problems.append("opening_bid_above_walk_away_maximum")
    if walk_away > affordability["max_price"]:
        problems.append("walk_away_maximum_above_affordability")
    return {
        "opening_bid": opening,
        "walk_away_maximum": walk_away,
        "conditions": [condition.strip() for condition in conditions],
        "affordable_maximum": affordability["max_price"],
        "asking_price": next(
            (f["value"] for f in case["facts"] if f["provenance"] == "listing" and f["key"] == "asking_price"),
            None,
        ),
        "monthly_cost_at_asking_price": affordability["monthly_cost"],
        "monthly_cost_at_walk_away_maximum": monthly_cost_at(walk_away),
    }, problems


def _is_amount(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
