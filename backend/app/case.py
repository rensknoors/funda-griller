"""Case builder (Dossier): pure assembly of Listing facts and computed metrics. No I/O, no judgement."""

from dataclasses import asdict
from datetime import date

from app.affordability import Rules, compute
from app.buyer_profile import BuyerProfile
from app.flags import RuleSet, evaluate, hard_no

LISTING_FACTS = (
    "address",
    "city",
    "status",
    "asking_price",
    "living_area",
    "plot_area",
    "rooms",
    "bedrooms",
    "construction_year",
    "energy_label",
    "heating",
)


def build_case(
    funda_id: str,
    snapshot: dict,
    profile_version: int | None,
    profile: BuyerProfile | None,
    rules: Rules,
    flag_rules: RuleSet,
    today: date,
) -> dict:
    affordability = (
        {
            **asdict(
                compute(profile, snapshot.get("asking_price"), snapshot.get("energy_label"), rules, today)
            ),
            "provenance": "computed",
            "computed_on": today.isoformat(),
        }
        if profile
        else None
    )
    facts = [
        {
            "key": key,
            "value": snapshot[key],
            "provenance": "listing",
            "fetched_at": snapshot["fetched_at"],
        }
        for key in LISTING_FACTS
        if snapshot.get(key) is not None
    ]
    flags = evaluate(flag_rules, _rule_inputs(snapshot, facts, affordability, profile))
    return {
        "funda_id": funda_id,
        "built_from": {
            "snapshot_id": snapshot["id"],
            "profile_version": profile_version,
            "flag_rules_version": flag_rules.version,
        },
        "facts": facts,
        "affordability": affordability,
        "flags": flags,
        "hard_no": hard_no(flag_rules, profile.deal_breakers, flags) if profile else None,
        "rules": {"year": rules.year, "is_current_year": rules.year == today.year},
    }


def _rule_inputs(
    snapshot: dict, facts: list[dict], affordability: dict | None, profile: BuyerProfile | None
) -> dict:
    """Everything a Flag rule may read, keyed by fact key. Only derived Buyer Profile values."""
    inputs = {fact["key"]: fact for fact in facts}
    if snapshot.get("description"):
        inputs["description"] = {
            "key": "description",
            "value": snapshot["description"],
            "provenance": "listing",
            "fetched_at": snapshot["fetched_at"],
        }
    if affordability and affordability["headroom"] is not None:
        inputs["headroom"] = {
            "key": "headroom",
            "value": affordability["headroom"],
            "provenance": "computed",
        }
    if profile:
        inputs["renovation_tolerance"] = {
            "key": "renovation_tolerance",
            "value": profile.renovation_tolerance,
            "provenance": "buyer_profile",
        }
        for key in ("must_haves", "deal_breakers"):
            inputs[key] = {"key": key, "value": getattr(profile, key), "provenance": "buyer_profile"}
    return inputs
