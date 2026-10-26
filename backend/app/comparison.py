"""One Listing's row in the comparison view, read off its snapshots and Case. Pure, no judgement:
the tier is whatever the Case or a Verdict already decided."""


def summarise(snapshots: list[dict], case: dict, tier: str | None = None) -> dict:
    """`snapshots` newest first. `tier` is the latest Verdict's tier, when one exists; a Hard no
    from the Case's deal-breakers always wins, since it is applied before any Verdict."""
    latest = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    hard_no = case["hard_no"]
    affordability = case["affordability"]
    woz = case["metrics"]["asking_vs_woz"]
    counts = {"pro": 0, "con": 0, "risk": 0}
    for flag in case["flags"]:
        counts[flag["class"]] += 1
    return {
        "tier": hard_no["tier"] if hard_no else tier,
        "hard_no_reason": hard_no["deal_breaker"] if hard_no else None,
        "status": latest.get("status"),
        "status_change": _change(previous, latest, "status"),
        "asking_price": latest.get("asking_price"),
        "previous_asking_price": (
            previous.get("asking_price") if _change(previous, latest, "asking_price") else None
        ),
        "living_area": latest.get("living_area"),
        "plot_area": latest.get("plot_area"),
        "energy_label": _energy_label(case["facts"], latest.get("energy_label")),
        "asking_vs_woz_percent": woz["percent"] if woz else None,
        "asking_vs_comparables_percent": case["metrics"]["asking_vs_comparables"]["percent"],
        "headroom": affordability["headroom"] if affordability else None,
        "renovation_direct": case["renovation_estimate"]["classes"]["direct"],
        "flag_counts": counts,
        "stale_count": sum(1 for fact in case["facts"] if fact.get("stale")),
        "last_fetched_at": latest["fetched_at"],
    }


def _change(previous: dict | None, latest: dict, key: str) -> dict | None:
    if previous is None or previous.get(key) == latest.get(key):
        return None
    return {"from": previous.get(key), "to": latest.get(key)}


def _energy_label(facts: list[dict], listing_label: str | None) -> dict | None:
    register = next(
        (
            f["value"]
            for f in facts
            if f["provenance"] == "source" and f["source"] == "energielabel" and f["key"] == "energy_label"
        ),
        None,
    )
    if isinstance(register, str):
        return {"value": register, "official": True}
    return {"value": listing_label, "official": False} if listing_label else None
