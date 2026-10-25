"""Case builder (Dossier): pure assembly of Listing facts and computed metrics. No I/O, no judgement."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
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
    "ownership_situation",
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
    "comparables": "third_party",
}


@dataclass(frozen=True)
class VersionedProfile:
    version: int
    profile: BuyerProfile


@dataclass(frozen=True)
class SourceInputs:
    """`names` are the configured Sources; `runs` maps each fetched one to its latest and latest
    succeeded run. Facts older than their Source's `ttl_days` are Stale; fewer comparables than
    `comparables_min_count` are thin."""

    names: list[str]
    runs: dict[str, dict] = field(default_factory=dict)
    ttl_days: dict[str, int] = field(default_factory=dict)
    comparables_min_count: int = 3


def build_case(
    funda_id: str,
    snapshot: dict,
    versioned_profile: VersionedProfile | None,
    rules: Rules,
    flag_rules: RuleSet,
    now: datetime,
    sources: SourceInputs,
    observation_runs: dict | None = None,
    documents: Sequence[dict] = (),
) -> dict:
    """Staleness is computed against `now`, never stored. `observation_runs` holds the latest and
    latest succeeded vision run over the snapshot's photo set. `documents` are the Listing's stored
    Documents; analysed ones contribute their Findings."""
    profile = versioned_profile.profile if versioned_profile else None
    source_runs = sources.runs
    today = now.date()
    computed_at = now.isoformat()
    source_facts = _source_facts(source_runs, sources.ttl_days, now)
    comparables_fetched = (source_runs.get("comparables") or {}).get("last_success") is not None
    register_label = _value(source_facts, "energielabel", "energy_label")
    # The register's label, when known, outranks the Listing's claim.
    energy_label = register_label if isinstance(register_label, str) else snapshot.get("energy_label")
    affordability = (
        {
            **asdict(compute(profile, snapshot.get("asking_price"), energy_label, rules, today)),
            # The label the borrowing capacity was computed with, so figures at other prices (the
            # Walk-away Maximum) rest on the same assumption.
            "energy_label": energy_label,
            "provenance": "computed",
            "computed_on": today.isoformat(),
            "computed_at": computed_at,
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
    ] + source_facts
    photos = [{"number": p["number"], "url": p["url"]} for p in snapshot.get("photos", [])]
    observed = (observation_runs or {}).get("last_success")
    facts += _observation_facts(observed, photos)
    facts += finding_facts(documents)
    vs_comparables = _asking_vs_comparables(
        snapshot, source_facts, comparables_fetched, sources.comparables_min_count
    )
    flags = evaluate(
        flag_rules, _rule_inputs(snapshot, facts, affordability, vs_comparables, profile), computed_at
    )
    return {
        "funda_id": funda_id,
        "built_from": {
            "snapshot_id": snapshot["id"],
            "profile_version": versioned_profile.version if versioned_profile else None,
            "flag_rules_version": flag_rules.version,
            "observation_run": observed["id"] if observed else None,
            "documents": [{"id": d["id"], "sha256": d["sha256"], "status": d["status"]} for d in documents],
        },
        "facts": facts,
        "sources": [_source_status(name, source_runs.get(name)) for name in sources.names],
        "photos": photos,
        "observations": _observation_status(photos, observation_runs),
        "documents": document_summaries(documents),
        "metrics": {
            name: {**metric, "computed_at": computed_at} if metric else None
            for name, metric in {
                "energy_label_check": _energy_label_check(snapshot.get("energy_label"), register_label),
                "asking_vs_woz": _asking_vs_woz(snapshot.get("asking_price"), source_facts),
                "asking_vs_comparables": vs_comparables,
            }.items()
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


def _asking_vs_comparables(snapshot: dict, facts: list[dict], fetched: bool, min_count: int) -> dict:
    """Asking price per m² against the median price per m² of the comparables that state both
    price and living area. Coverage states plainly when there are none or too few to lean on."""
    per_m2 = sorted(
        c["asking_price"] / c["living_area"]
        for c in (f["value"] for f in facts if f["source"] == "comparables" and f["key"] == "comparable")
        if _positive(c.get("asking_price")) and _positive(c.get("living_area"))
    )
    count = len(per_m2)
    coverage = "not_fetched" if not fetched else "none" if count == 0 else "thin" if count < min_count else "sufficient"
    asking, area = snapshot.get("asking_price"), snapshot.get("living_area")
    median = _median(per_m2) if per_m2 else None
    comparable = median is not None and _positive(asking) and _positive(area)
    return {
        "coverage": coverage,
        "count": count,
        "min_count": min_count,
        "price_per_m2": round(asking / area) if _positive(asking) and _positive(area) else None,
        "median_price_per_m2": round(median) if median is not None else None,
        "percent": round((asking / area / median - 1) * 100, 1) if comparable else None,
        "comparables_value": round(median * area) if median is not None and _positive(area) else None,
        "provenance": "computed",
    }


def _positive(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _median(values: list[float]) -> float:
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


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


def _observation_facts(run: dict | None, photos: list[dict]) -> list[dict]:
    """Observations as Case facts: estimated, each citing the photos it was read from."""
    if run is None:
        return []
    by_number = {photo["number"]: photo for photo in photos}
    return [
        {
            "key": observation["key"],
            "value": observation["value"],
            "note": observation["note"],
            "photos": [by_number[n] for n in observation["photos"] if n in by_number],
            "provenance": "observation",
            "estimated": True,
            "extracted_at": run["attempted_at"],
            "model": run["model"],
        }
        for observation in run["observations"]
    ]


def _observation_status(photos: list[dict], runs: dict | None) -> dict:
    latest = (runs or {}).get("latest")
    if latest:
        status, reason = latest["outcome"], latest["reason"]
    else:
        status, reason = ("not_run", None) if photos else ("no_photos", None)
    return {
        "status": status,
        "reason": reason,
        "attempted_at": latest["attempted_at"] if latest else None,
        "model": latest["model"] if latest else None,
    }


def _rule_inputs(
    snapshot: dict,
    facts: list[dict],
    affordability: dict | None,
    vs_comparables: dict,
    profile: BuyerProfile | None,
) -> dict:
    """Everything a Flag rule may read, keyed by fact key. Only derived Buyer Profile values."""
    inputs = {fact["key"]: fact for fact in facts if fact["provenance"] == "listing"}
    # Source facts are keyed `<source>.<key>` (e.g. `woz.woz_value`), so the register's
    # energielabel never shadows the Listing's claim; the value with the latest `as_of` wins.
    for fact in sorted(
        (f for f in facts if f["provenance"] == "source"), key=lambda f: f["as_of"] or ""
    ):
        inputs[f"{fact['source']}.{fact['key']}"] = fact
    # Observations are keyed `observation.<key>` (e.g. `observation.damp_or_mould`).
    for fact in facts:
        if fact["provenance"] == "observation":
            inputs[f"observation.{fact['key']}"] = fact
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
    # Only sufficient comparables may say the ask is high: thin ones are not a market.
    if vs_comparables["coverage"] == "sufficient" and vs_comparables["percent"] is not None:
        inputs["asking_vs_comparables_percent"] = {
            "key": "asking_vs_comparables_percent",
            "value": vs_comparables["percent"],
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
