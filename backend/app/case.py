"""Case builder (Dossier): pure assembly of Listing facts and computed metrics. No I/O, no judgement."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

from app.affordability import Rules, compute, rules_summary
from app.buyer_profile import BuyerProfile
from app.findings import USER_DOCUMENT_KIND, document_summaries, finding_facts
from app.flags import RuleSet, evaluate, hard_no
from app.house_type import AskingPriceMargins, category, kind
from app.price_index import PriceIndex, peildatum
from app.renovation import CostTable, estimate

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
    "house_type",
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
    # OpenRouteService travel times over OpenStreetMap: a model of the road network, not a register.
    "commute": "third_party",
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
    levering: date,
    flag_rules: RuleSet,
    cost_table: CostTable,
    price_index: PriceIndex,
    bid_margins: AskingPriceMargins,
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
    source_facts, commute_coverage = _current_commute(
        _source_facts(source_runs, sources.ttl_days, now), profile, "commute" in sources.names
    )
    comparables_fetched = (source_runs.get("comparables") or {}).get("last_success") is not None
    register_label = _value(source_facts, "energielabel", "energy_label")
    # The register's label, when known, outranks the Listing's claim.
    energy_label = register_label if isinstance(register_label, str) else snapshot.get("energy_label")
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
    vs_woz = _asking_vs_woz(snapshot.get("asking_price"), source_facts, price_index, today)
    vs_comparables = _asking_vs_comparables(
        snapshot, source_facts, comparables_fetched, sources.comparables_min_count
    )
    # The Renovation Estimate reads no Buyer Profile and no affordability: it is the same for every
    # household, and its Direct nodig midpoint lowers what the household can pay for this house.
    renovation = estimate(
        cost_table,
        _rule_inputs(snapshot, facts, None, vs_comparables, None, None, vs_woz),
        _missing_renovation_inputs(facts, photos, observed, documents, energy_label),
        computed_at,
    )
    affordability = (
        {
            **asdict(
                compute(
                    profile, snapshot.get("asking_price"), energy_label, rules, levering, renovation["direct_midpoint"]
                )
            ),
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
    flags = evaluate(
        flag_rules, _rule_inputs(snapshot, facts, affordability, vs_comparables, renovation, profile, vs_woz), computed_at
    )
    return {
        "funda_id": funda_id,
        "built_from": {
            "snapshot_id": snapshot["id"],
            "profile_version": versioned_profile.version if versioned_profile else None,
            "flag_rules_version": flag_rules.version,
            "cost_table_version": cost_table.version,
            "price_index_version": price_index.version,
            "bid_margins_version": bid_margins.version,
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
                "asking_vs_woz": vs_woz,
                "asking_vs_comparables": vs_comparables,
                "commute_coverage": commute_coverage,
            }.items()
        },
        "affordability": affordability,
        # The average overbid for the soort woning: the margin a weakly grounded Walk-away Maximum
        # may sit above the asking price. A value from a versioned rule table.
        "asking_price_margin": {
            **bid_margins.for_category(category(snapshot.get("object_type"), snapshot.get("house_type"))),
            "provenance": "rule",
            "computed_at": computed_at,
        },
        "renovation_estimate": renovation,
        "flags": flags,
        "hard_no": hard_no(flag_rules, profile.deal_breakers, flags) if profile else None,
        "rules": rules_summary(rules, levering, profile),
    }


def _missing_renovation_inputs(
    facts: list[dict], photos: list[dict], observed: dict | None, documents: Sequence[dict], energy_label: object
) -> list[str]:
    """What the Renovation Estimate had no facts from: Observations (no photos, or none read yet), a
    Document the user added (the Vragenlijst and the like; the funda brochure does not count) and an
    energielabel from the register or the Listing."""
    missing = []
    if not photos or observed is None:
        missing.append("observations")
    if not any(d["kind"] == USER_DOCUMENT_KIND and d["status"] == "analysed" for d in documents):
        missing.append("vragenlijst")
    if not energy_label:
        missing.append("energielabel")
    return missing


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


def _asking_vs_woz(asking_price: int | None, facts: list[dict], price_index: PriceIndex, today: date) -> dict | None:
    """The asking price against the latest WOZ value, as it is and brought from its peildatum to
    today's prices with the house price index (None when the peildatum is outside the series)."""
    woz = [
        (dated, f["value"])
        for f in facts
        if f["source"] == "woz"
        and f["key"] == "woz_value"
        and isinstance(f["value"], int)
        and f["value"] > 0
        and (dated := peildatum(f["as_of"])) is not None
    ]
    if asking_price is None or not woz:
        return None
    as_of, value = max(woz)
    indexed = price_index.bring_to(value, as_of, today)
    return {
        "asking_price": asking_price,
        "woz_value": value,
        "woz_as_of": as_of.isoformat(),
        "difference": asking_price - value,
        "percent": round((asking_price - value) / value * 100, 1),
        "indexed": {
            "woz_value": indexed.value,
            "index_from": indexed.index_from,
            "index_to": indexed.index_to,
            "difference": asking_price - indexed.value,
            "percent": round((asking_price - indexed.value) / indexed.value * 100, 1),
            "source": price_index.source,
        }
        if indexed
        else None,
        "provenance": "computed",
    }


def _asking_vs_comparables(snapshot: dict, facts: list[dict], fetched: bool, min_count: int) -> dict:
    """Asking price per m² against the median price per m² of the comparables that state both
    price and living area and are of the same kind (an apartment is no comparable for a house).
    With enough of the same soort woning (tussenwoning, vrijstaand, ...) only those count. Coverage
    states plainly when there are none or too few to lean on."""
    usable = [
        c
        for c in (f["value"] for f in facts if f["source"] == "comparables" and f["key"] == "comparable")
        if _positive(c.get("asking_price")) and _positive(c.get("living_area"))
    ]
    chosen, matched_on = _same_type(snapshot, usable, min_count)
    per_m2 = sorted(c["asking_price"] / c["living_area"] for c in chosen)
    count = len(per_m2)
    coverage = "not_fetched" if not fetched else "none" if count == 0 else "thin" if count < min_count else "sufficient"
    asking, area = snapshot.get("asking_price"), snapshot.get("living_area")
    median = _median(per_m2) if per_m2 else None
    comparable = median is not None and _positive(asking) and _positive(area)
    return {
        "coverage": coverage,
        "count": count,
        "min_count": min_count,
        "matched_on": matched_on,
        "excluded": len(usable) - count,
        "price_per_m2": round(asking / area) if _positive(asking) and _positive(area) else None,
        "median_price_per_m2": round(median) if median is not None else None,
        "percent": round((asking / area / median - 1) * 100, 1) if comparable else None,
        "comparables_value": round(median * area) if median is not None and _positive(area) else None,
        "provenance": "computed",
    }


def _same_type(snapshot: dict, comparables: list[dict], min_count: int) -> tuple[list[dict], str | None]:
    """The comparables of the Listing's soort woning when at least `min_count` of them remain, else
    those of its kind (a comparable of unknown kind is given the benefit of the doubt). Says which
    it matched on; None when the Listing's own type is unknown."""
    own_kind = kind(snapshot.get("object_type"), snapshot.get("house_type"))
    if own_kind is None:
        return comparables, None
    same_kind = [c for c in comparables if kind(c.get("object_type"), c.get("house_type")) in (None, own_kind)]
    own_category = category(snapshot.get("object_type"), snapshot.get("house_type"))
    same_category = [c for c in same_kind if own_category and category(c.get("object_type"), c.get("house_type")) == own_category]
    if own_category and len(same_category) >= min_count:
        return same_category, "house_type"
    return same_kind, "object_type"


def _as_of_order(fact: dict) -> str:
    """Sort key for a Source fact's date: ISO when it reads as one (WOZ values come as "1 jan
    2025"), else the text as it is."""
    dated = peildatum(fact["as_of"])
    return dated.isoformat() if dated else fact["as_of"] or ""


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


def _current_commute(
    facts: list[dict], profile: BuyerProfile | None, configured: bool
) -> tuple[list[dict], dict | None]:
    """A commute travel time counts only for a current Buyer Profile destination at the address it
    was computed for: one for a removed destination or an older address leaves the Case, and a
    destination without one is listed as not fetched, so it is never judged on an old figure. The
    address fingerprint stays out of the Case."""
    refs = {d.label: d.address_ref for d in profile.commute_destinations} if profile else {}
    current, fetched = [], set()
    for fact in facts:
        if fact["source"] != "commute" or fact["key"] != "travel_minutes":
            current.append(fact)
            continue
        travel = dict(fact["value"])
        label, address_ref = travel["destination"], travel.pop("address_ref", None)
        if label in refs and refs[label] == address_ref:
            fetched.add(label)
            current.append({**fact, "value": travel})
    not_fetched = [label for label in refs if label not in fetched]
    coverage = {"not_fetched": not_fetched, "provenance": "computed"} if configured and not_fetched else None
    return current, coverage


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
    renovation: dict | None,
    profile: BuyerProfile | None,
    vs_woz: dict | None,
) -> dict:
    """Everything a Flag rule may read, keyed by fact key. Only derived Buyer Profile values.
    `renovation` (the Renovation Estimate) is None while the estimate itself is being built."""
    inputs = {fact["key"]: fact for fact in facts if fact["provenance"] == "listing"}
    # Source facts are keyed `<source>.<key>` (e.g. `woz.woz_value`), so the register's
    # energielabel never shadows the Listing's claim; the value with the latest `as_of` wins.
    for fact in sorted((f for f in facts if f["provenance"] == "source"), key=_as_of_order):
        inputs[f"{fact['source']}.{fact['key']}"] = fact
    # Commute travel times, one per destination, are keyed `commute.travel_minutes:<label>`, with
    # the faster mode's minutes as the value and the travel time (modes included) beside it.
    # Unknown ones (address not found, no route) are left out: they raise nothing.
    for fact in facts:
        if fact["provenance"] == "source" and fact["source"] == "commute" and fact["key"] == "travel_minutes":
            travel = fact["value"]
            if travel["minutes"] is not None:
                inputs[f"commute.travel_minutes:{travel['destination']}"] = {
                    **fact,
                    "value": travel["minutes"],
                    "commute": travel,
                }
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
    # The WOZ value in today's prices; the raw one lags the market by its peildatum.
    if vs_woz and vs_woz["indexed"]:
        inputs["indexed_woz_value"] = {
            "key": "indexed_woz_value",
            "value": vs_woz["indexed"]["woz_value"],
            "provenance": "computed",
        }
    # Only sufficient comparables may say the ask is high: thin ones are not a market.
    if vs_comparables["coverage"] == "sufficient" and vs_comparables["percent"] is not None:
        inputs["asking_vs_comparables_percent"] = {
            "key": "asking_vs_comparables_percent",
            "value": vs_comparables["percent"],
            "provenance": "computed",
        }
    if renovation:
        inputs["renovation.direct_midpoint"] = {
            "key": "renovation_direct_midpoint",
            "value": renovation["direct_midpoint"],
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
        # Labels and limits only: the destination address stays out of the Case.
        inputs["commute_destinations"] = {
            "key": "commute_destinations",
            "value": [{"label": d.label, "max_minutes": d.max_minutes} for d in profile.commute_destinations],
            "provenance": "buyer_profile",
        }
    return inputs
