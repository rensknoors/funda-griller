"""The Listings list as comparison view: per-Listing key figures, Stale counts, archive, status change."""

from app.ports import SourceFact
from tests.listing_fixtures import LIVE_URL, SOLD_URL, live_listing, sold_listing
from tests.profile_fixtures import low_income_profile, typical_profile


def capture(client, listing_provider, url=LIVE_URL, listing=None):
    listing_provider.listings[url] = listing or live_listing()
    return client.post("/api/listings", json={"url": url})


def listed(client, **params):
    return {item["funda_id"]: item for item in client.get("/api/listings", params=params).json()}


def comparison(client, funda_id="80907644"):
    return listed(client)[funda_id]["comparison"]


def test_list_shows_price_area_and_key_metrics_per_listing(client, listing_provider, source_clients):
    source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
    source_clients["woz"].facts = [SourceFact("woz_value", 500_000, "2025-01-01")]
    client.put("/api/buyer-profile", json=typical_profile())
    capture(client, listing_provider)

    row = comparison(client)

    assert row["asking_price"] == 595_000
    assert (row["living_area"], row["plot_area"]) == (152, 410)
    assert row["energy_label"] == {"value": "A", "official": True}
    assert row["asking_vs_woz_percent"] == 19.0
    case = client.get("/api/listings/80907644/case").json()
    assert row["headroom"] == case["affordability"]["headroom"] > 0
    assert row["flag_counts"] == {"pro": 1, "con": 1, "risk": 0}
    assert row["status"] == "available"


def test_without_register_label_the_listing_claim_is_shown(client, listing_provider):
    capture(client, listing_provider)

    row = comparison(client)

    assert row["energy_label"] == {"value": "B", "official": False}
    assert row["asking_vs_woz_percent"] is None
    assert row["headroom"] is None


def test_tier_is_empty_until_a_verdict_exists(client, listing_provider):
    client.put("/api/buyer-profile", json=typical_profile())
    capture(client, listing_provider)

    row = comparison(client)

    assert row["tier"] is None
    assert row["hard_no_reason"] is None


def test_a_deal_breaker_hit_shows_as_hard_no_with_its_reason(client, listing_provider):
    client.put("/api/buyer-profile", json=low_income_profile() | {"deal_breakers": ["Boven budget"]})
    capture(client, listing_provider)

    row = comparison(client)

    assert row["tier"] == "hard_no"
    assert row["hard_no_reason"] == "Boven budget"


def test_stale_source_facts_are_counted_per_listing(client, listing_provider, source_clients, clock):
    source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
    source_clients["woz"].facts = [
        SourceFact("woz_value", 371_000, "2024-01-01"),
        SourceFact("woz_value", 392_000, "2025-01-01"),
    ]
    capture(client, listing_provider)
    assert comparison(client)["stale_count"] == 0

    clock.advance(400)

    row = comparison(client)
    assert row["stale_count"] == 3
    assert row["last_fetched_at"] == "2026-10-24T12:00:00+00:00"


def test_a_status_change_after_refetch_is_reported(client, listing_provider, clock):
    capture(client, listing_provider)
    assert comparison(client)["status_change"] is None
    clock.advance(3)
    listing_provider.listings[LIVE_URL] = live_listing(raw_status="Verkocht", asking_price=570_000)

    refetched = client.post("/api/listings/80907644/refetch").json()

    row = refetched["comparison"]
    assert row["status"] == "sold"
    assert row["status_change"] == {"from": "available", "to": "sold"}
    assert row["previous_asking_price"] == 595_000
    assert row["last_fetched_at"] == "2026-10-27T12:00:00+00:00"


def test_an_unchanged_refetch_reports_no_status_change(client, listing_provider):
    capture(client, listing_provider)

    row = client.post("/api/listings/80907644/refetch").json()["comparison"]

    assert row["status_change"] is None
    assert row["previous_asking_price"] is None


def test_archived_listings_are_hidden_by_default_and_counted(client, listing_provider):
    capture(client, listing_provider)
    capture(client, listing_provider, SOLD_URL, sold_listing())

    archived = client.post("/api/listings/43117443/archive")

    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert list(listed(client)) == ["80907644"]
    everything = listed(client, include_archived="true")
    assert {k: v["archived"] for k, v in everything.items()} == {"80907644": False, "43117443": True}


def test_restoring_an_archived_listing_keeps_its_history(client, listing_provider):
    capture(client, listing_provider)
    client.post("/api/listings/80907644/refetch")
    client.post("/api/listings/80907644/archive")

    restored = client.post("/api/listings/80907644/restore")

    assert restored.status_code == 200
    assert restored.json()["archived"] is False
    listing = listed(client)["80907644"]
    assert listing["archived"] is False
    assert len(listing["snapshots"]) == 2
    assert client.get("/api/listings/80907644/case").status_code == 200


def test_archiving_an_unknown_listing_is_not_found(client):
    assert client.post("/api/listings/12345678/archive").status_code == 404
    assert client.post("/api/listings/12345678/restore").status_code == 404
