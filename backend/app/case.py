"""Case builder (Dossier): pure assembly of Listing facts and computed metrics. No I/O, no judgement."""

from datetime import date

from app.affordability import Rules, compute
from app.buyer_profile import BuyerProfile

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
    today: date,
) -> dict:
    affordability = (
        {
            **compute(profile, snapshot.get("asking_price"), snapshot.get("energy_label"), rules, today),
            "provenance": "computed",
            "computed_on": today.isoformat(),
        }
        if profile
        else None
    )
    return {
        "funda_id": funda_id,
        "built_from": {"snapshot_id": snapshot["id"], "profile_version": profile_version},
        "facts": [
            {
                "key": key,
                "value": snapshot[key],
                "provenance": "listing",
                "fetched_at": snapshot["fetched_at"],
            }
            for key in LISTING_FACTS
            if snapshot.get(key) is not None
        ],
        "affordability": affordability,
        "rules": {"year": rules.year, "is_current_year": rules.year == today.year},
    }
