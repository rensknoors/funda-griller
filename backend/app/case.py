"""Case builder (Dossier): pure assembly of Listing facts and computed metrics. No I/O, no judgement."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime, timedelta

from app.affordability import Rules, compute
from app.buyer_profile import BuyerProfile
from app.findings import document_summaries, finding_facts
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

# How far a Source's facts can be trusted. WOZ comes from a third-party price-history service,
# not from an official register. Flood and soil risk (Klimaateffectatlas, publishing LIWO and
# Deltares maps for the national government) and noise (RIVM) are official public maps. Unknown
# Sources are treated as third-party.
SOURCE_TRUST = {
    "energielabel": "official",
    "woz": "third_party",
    "flood_soil": "official",
    "noise": "official",
}


def build_case(
    funda_id: str,
    snapshot: dict,
    profile_version: int | None,
    profile: BuyerProfile | None,
    rules: Rules,
    flag_rules: RuleSet,
    now: datetime,
    sources: list[str],
    source_runs: dict[str, dict],
    ttl_days: dict[str, int],
    documents: Sequence[dict] = (),
) -> dict:
    """`sources` are the configured Source names; `source_runs` maps each to its latest and
    latest succeeded run. Staleness is computed against `now`, never stored. `documents` are the
    Listing's stored Documents; analysed ones contribute their Findings."""
    today = now.date()
    source_facts = _source_facts(source_runs, ttl_days, now)
    register_label = _value(source_facts, "energielabel", "energy_label")
    # The register's label, when known, outranks the Listing's claim.
    energy_label = register_label if isinstance(register_label, str) else snapshot.get("energy_label")
    affordability = (
        {
            **asdict(compute(profile, snapshot.get("asking_price"), energy_label, rules, today)),
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
    ] + source_facts + finding_facts(documents)
    flags = evaluate(flag_rules, _rule_inputs(snapshot, facts, affordability, profile))
    return {
        "funda_id": funda_id,
        "built_from": {
            "snapshot_id": snapshot["id"],
            "profile_version": profile_version,
            "flag_rules_version": flag_rules.version,
            "documents": [{"id": d["id"], "sha256": d["sha256"], "status": d["status"]} for d in documents],
        },
        "facts": facts,
        "sources": [_source_status(name, source_runs.get(name)) for name in sources],
        "documents": document_summaries(documents),
        "metrics": {
            "energy_label_check": _energy_label_check(snapshot.get("energy_label"), register_label),
            "asking_vs_woz": _asking_vs_woz(snapshot.get("asking_price"), source_facts),
        },
        "affordability": affordability,
        "flags": flags,
        "hard_no": hard_no(flag_rules, profile.deal_breakers, flags) if profile else None,
        "rules": {"year": rules.year, "is_current_year": rules.year == today.year},
    }


def _source_status(source: str, runs: dict | None) -> dict:
    latest = runs["latest"] if runs else None
    return {
        "source": source,
        "status": latest["outcome"] if latest else "skipped",
        "reason": latest["reason"] if latest else "not_fetched",
        "attempted_at": latest["attempted_at"] if latest else None,
        "trust": SOURCE_TRUST.get(source, "third_party"),
    }


def _value(facts: list[dict], source: str, key: str) -> object:
    return next((f["value"] for f in facts if f["source"] == source and f["key"] == key), None)


def _energy_label_check(listing_label: str | None, register_label: object) -> dict | None:
    """States whether the Listing's claimed label equals the register's. A fact, not a judgement."""
    if listing_label is None or not isinstance(register_label, str):
        return None
    return {
        "listing": listing_label,
        "register": register_label,
        "matches": listing_label.strip().upper() == register_label.strip().upper(),
        "provenance": "computed",
    }


def _asking_vs_woz(asking_price: int | None, facts: list[dict]) -> dict | None:
    woz = [
        f
        for f in facts
        if f["source"] == "woz" and f["key"] == "woz_value" and f["as_of"] and isinstance(f["value"], int) and f["value"] > 0
    ]
    if asking_price is None or not woz:
        return None
    latest = max(woz, key=lambda f: f["as_of"])
    difference = asking_price - latest["value"]
    return {
        "asking_price": asking_price,
        "woz_value": latest["value"],
        "woz_as_of": latest["as_of"],
        "difference": difference,
        "percent": round(difference / latest["value"] * 100, 1),
        "provenance": "computed",
    }


def _source_facts(source_runs: dict[str, dict], ttl_days: dict[str, int], now: datetime) -> list[dict]:
    facts = []
    for source, runs in source_runs.items():
        run = runs["last_success"]
        if run is None:
            continue
        ttl = ttl_days.get(source)
        stale = ttl is not None and now - datetime.fromisoformat(run["attempted_at"]) > timedelta(days=ttl)
        facts.extend(
            {
                "key": fact["name"],
                "value": fact["value"],
                "as_of": fact["as_of"],
                "provenance": "source",
                "source": source,
                "trust": SOURCE_TRUST.get(source, "third_party"),
                "fetched_at": run["attempted_at"],
                "ttl_days": ttl,
                "stale": stale,
            }
            for fact in run["facts"]
        )
    return facts


def _rule_inputs(
    snapshot: dict, facts: list[dict], affordability: dict | None, profile: BuyerProfile | None
) -> dict:
    """Everything a Flag rule may read, keyed by fact key. Only derived Buyer Profile values."""
    inputs = {fact["key"]: fact for fact in facts if fact["provenance"] == "listing"}
    # Source facts are keyed `<source>.<key>` (e.g. `woz.woz_value`), so the register's
    # energielabel never shadows the Listing's claim; the value with the latest `as_of` wins.
    for fact in sorted(
        (f for f in facts if f["provenance"] == "source"), key=lambda f: f["as_of"] or ""
    ):
        inputs[f"{fact['source']}.{fact['key']}"] = fact
    # Findings are keyed `finding.<topic>`. When Documents disagree, a disclosure (`True`) wins
    # over a denial, so a seller's admission is never hidden by another page.
    for fact in sorted((f for f in facts if f["provenance"] == "finding"), key=lambda f: f["value"] is True):
        inputs[f"finding.{fact['key']}"] = fact
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
