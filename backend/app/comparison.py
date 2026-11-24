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
        # As the Case counts them: a Correction outranks the Listing (and the register's label).
        "living_area": _kenmerk_value(case["facts"], "living_area"),
        "plot_area": _kenmerk_value(case["facts"], "plot_area"),
        "energy_label": _energy_label(case["facts"]),
        # Against the WOZ value in today's prices when it can be indexed; the raw one lags the market.
        "asking_vs_woz_percent": (woz["indexed"] or woz)["percent"] if woz else None,
        "asking_vs_comparables_percent": case["metrics"]["asking_vs_comparables"]["percent"],
        # Headroom is at the Expected Sale Price; the Prijsstelling is the asking price against it.
        "asking_vs_expected_percent": (
            case["metrics"]["asking_vs_expected"]["percent"] if case["metrics"]["asking_vs_expected"] else None
        ),
        "expected_sale_price": case["metrics"]["expected_sale_price"]["value"],
        "headroom": affordability["headroom"] if affordability else None,
        "renovation_direct": case["renovation_estimate"]["classes"]["direct"],
        "flag_counts": counts,
        "stale_count": sum(1 for fact in case["facts"] if fact.get("stale")),
        "stale_sources": _stale_sources(case["facts"]),
        "last_fetched_at": latest["fetched_at"],
    }


def _stale_sources(facts: list[dict]) -> list[dict]:
    """Per Source with Stale facts: how many, when they were fetched and how long they are valid,
    so the list can say what is Verouderd and offer to refetch just that Source."""
    by_source: dict[str, dict] = {}
    for fact in facts:
        if not fact.get("stale"):
            continue
        entry = by_source.setdefault(
            fact["source"],
            {"source": fact["source"], "facts": 0, "fetched_at": fact["fetched_at"], "ttl_days": fact["ttl_days"]},
        )
        entry["facts"] += 1
    return sorted(by_source.values(), key=lambda s: s["fetched_at"])


def _change(previous: dict | None, latest: dict, key: str) -> dict | None:
    if previous is None or previous.get(key) == latest.get(key):
        return None
    return {"from": previous.get(key), "to": latest.get(key)}


def _kenmerk(facts: list[dict], key: str) -> dict | None:
    """The Listing's fact, or the household's Correction in its place."""
    return next((f for f in facts if f["key"] == key and f["provenance"] in ("listing", "correction")), None)


def _kenmerk_value(facts: list[dict], key: str) -> object:
    kenmerk = _kenmerk(facts, key)
    return kenmerk["value"] if kenmerk else None


def _energy_label(facts: list[dict]) -> dict | None:
    """The energielabel the Case counts with: a Correction, else the register's, else the Listing's."""
    kenmerk = _kenmerk(facts, "energy_label")
    if kenmerk and kenmerk["provenance"] == "correction":
        return {"value": kenmerk["value"], "official": False, "corrected": True}
    register = next(
        (
            f["value"]
            for f in facts
            if f["provenance"] == "source" and f["source"] == "energielabel" and f["key"] == "energy_label"
        ),
        None,
    )
    if isinstance(register, str):
        return {"value": register, "official": True, "corrected": False}
    return {"value": kenmerk["value"], "official": False, "corrected": False} if kenmerk else None
