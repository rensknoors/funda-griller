"""Renovation Estimate (Verbouwingsraming): what the house may cost to renovate, split by urgency.

Pure arithmetic over a versioned cost table, no I/O and no judgement (ADR-0001). An item enters the
estimate only when a Case fact triggers it, in the Flag rule condition vocabulary; nothing is
guessed. Every item is an estimate: a low–high range from public average prices, citing the facts
behind it. The estimate is the same for every Buyer Profile.
"""

from dataclasses import dataclass

from app.flags import DERIVED, holds

# Most urgent first: Direct nodig, Binnen 5 jaar, Optioneel.
URGENCIES = ("direct", "within_5_years", "optional")


@dataclass(frozen=True)
class CostTable:
    """`size_bands` are the living-area limits (m²) between the small, middle and large band;
    `assumed_living_area` prices a per-m² item when the Listing states no living area."""

    version: int
    size_bands: tuple[int, int]
    assumed_living_area: int
    items: tuple[dict, ...]


def estimate(table: CostTable, facts: dict[str, dict], missing_inputs: list[str], computed_at: str) -> dict:
    """The Renovation Estimate over the Case facts (keyed as for the Flag rules). One item per cost
    table id, citing every fact that triggered it and taking the most urgent class; an item another
    present item `supersedes` is dropped. `missing_inputs` names what could have triggered more."""
    triggered = {}
    for item in table.items:
        urgency, evidence = _triggered(item, facts)
        if urgency is not None:
            triggered[item["id"]] = (item, urgency, evidence)
    superseded = {gone for item, _, _ in triggered.values() for gone in item.get("supersedes", ())}
    items = [
        _priced(table, item, urgency, evidence, facts.get("living_area"))
        for item_id, (item, urgency, evidence) in triggered.items()
        if item_id not in superseded
    ]
    classes = {urgency: _total([i for i in items if i["urgency"] == urgency]) for urgency in URGENCIES}
    return {
        "cost_table_version": table.version,
        "items": items,
        "classes": classes,
        "direct_midpoint": classes["direct"]["midpoint"],
        "missing_inputs": missing_inputs,
        "provenance": "computed",
        "computed_at": computed_at,
    }


def _triggered(item: dict, facts: dict[str, dict]) -> tuple[str | None, list[dict]]:
    urgency, evidence = None, []
    for trigger in item["triggers"]:
        found = _trigger_evidence(trigger, facts)
        if found is None:
            continue
        candidate = trigger.get("urgency", item["urgency"])
        if urgency is None or URGENCIES.index(candidate) < URGENCIES.index(urgency):
            urgency = candidate
        evidence += [fact for fact in found if fact not in evidence]
    return urgency, evidence


def _trigger_evidence(trigger: dict, facts: dict[str, dict]) -> list[dict] | None:
    """The facts a trigger cites when it and all its `also` conditions hold, else None. Rule
    thresholds are not facts and are left out."""
    evidence: list[dict] = []
    for condition in (trigger, *trigger.get("also", ())):
        hits = holds(condition, facts)
        if not hits:
            return None
        evidence += [fact for found in hits for fact in found if fact["provenance"] not in DERIVED]
    return evidence


def _priced(table: CostTable, item: dict, urgency: str, evidence: list[dict], living_area: dict | None) -> dict:
    basis = item["basis"]
    area = living_area["value"] if living_area else None
    if basis == "fixed":
        low, high = item["low"], item["high"]
    elif basis == "per_m2":
        size = area if area is not None else table.assumed_living_area
        low, high = item["low"] * size, item["high"] * size
    else:  # size_band
        band = 1 if area is None else 0 if area < table.size_bands[0] else 1 if area <= table.size_bands[1] else 2
        low, high = item["low"][band], item["high"][band]
    sized = basis != "fixed" and living_area is not None
    return {
        "id": item["id"],
        "label": item["label"],
        "urgency": urgency,
        "low": round(low),
        "high": round(high),
        "basis": basis,
        "size_assumed": basis != "fixed" and area is None,
        "inspection": item.get("inspection", False),
        "source": item["source"],
        "price_year": item["price_year"],
        "estimated": True,
        "evidence": evidence + ([living_area] if sized and living_area not in evidence else []),
    }


def _total(items: list[dict]) -> dict:
    low, high = sum(i["low"] for i in items), sum(i["high"] for i in items)
    return {"low": low, "high": high, "midpoint": (low + high) // 2}
