from app.ports import ListingError, ListingRemoved, ProviderBlocked
from tests.listing_fixtures import LIVE_URL, SOLD_URL, live_listing, sold_listing


def test_pasting_a_url_captures_a_snapshot_shown_in_the_list(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()

    created = client.post("/api/listings", json={"url": LIVE_URL})

    assert created.status_code == 201
    body = created.json()
    assert body["funda_id"] == "80907644"
    snapshot = body["snapshots"][0]
    assert (snapshot["address"], snapshot["city"]) == ("Buchterweg 15", "Holtum")
    assert snapshot["asking_price"] == 595000
    assert snapshot["living_area"] == 152
    assert snapshot["plot_area"] == 410
    assert snapshot["rooms"] == 6
    assert snapshot["construction_year"] == 1931
    assert snapshot["energy_label"] == "B"
    assert snapshot["latitude"] == 51.0
    assert snapshot["heating"] == "Warmtepomp"
    assert snapshot["description"].startswith("Vrijstaande")
    listed = client.get("/api/listings").json()
    assert [item["funda_id"] for item in listed] == ["80907644"]


def test_snapshot_keeps_raw_status_history_and_media_urls(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()

    snapshot = client.post("/api/listings", json={"url": LIVE_URL}).json()["snapshots"][0]

    assert snapshot["raw_status"] == "Beschikbaar"
    assert snapshot["status"] == "available"
    assert snapshot["price_history"] == [{"date": "2026-10-21", "price": 595000}]
    assert snapshot["photo_urls"] == [
        "https://cloud.funda.nl/p1.jpg",
        "https://cloud.funda.nl/p2.jpg",
    ]
    assert snapshot["brochure_url"] == "https://cloud.funda.nl/brochure.pdf"


def test_listing_is_keyed_on_url_id_and_keeps_provider_id_separately(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()

    body = client.post("/api/listings", json={"url": LIVE_URL}).json()

    assert body["funda_id"] == "80907644"
    assert body["snapshots"][0]["provider_id"] == "17270371"


def test_sold_listing_without_optional_data_is_captured(client, listing_provider):
    listing_provider.listings[SOLD_URL] = sold_listing()

    response = client.post("/api/listings", json={"url": SOLD_URL})

    assert response.status_code == 201
    snapshot = response.json()["snapshots"][0]
    assert snapshot["raw_status"] == "Verkocht"
    assert snapshot["status"] == "sold"
    assert snapshot["photo_urls"] == []
    assert snapshot["brochure_url"] is None


def test_unmapped_raw_status_is_kept_and_shown_unknown(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing(raw_status="Onder voorbehoud")

    snapshot = client.post("/api/listings", json={"url": LIVE_URL}).json()["snapshots"][0]

    assert snapshot["raw_status"] == "Onder voorbehoud"
    assert snapshot["status"] == "unknown"


def test_bad_url_is_rejected_without_calling_the_provider(client, listing_provider):
    response = client.post("/api/listings", json={"url": "https://example.com/huis/1"})

    assert response.status_code == 400
    assert response.json()["code"] == "bad_url"
    assert listing_provider.calls == []


def test_removed_listing_is_reported_as_removed(client, listing_provider):
    listing_provider.listings[LIVE_URL] = ListingRemoved()

    response = client.post("/api/listings", json={"url": LIVE_URL})

    assert response.status_code == 404
    assert response.json()["code"] == "listing_removed"
    assert client.get("/api/listings").json() == []


def test_blocked_provider_is_reported_as_blocked(client, listing_provider):
    listing_provider.listings[LIVE_URL] = ProviderBlocked()

    response = client.post("/api/listings", json={"url": LIVE_URL})

    assert response.status_code == 502
    assert response.json()["code"] == "provider_blocked"


def test_pasting_a_captured_url_offers_refetch_instead_of_duplicating(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})

    again = client.post("/api/listings", json={"url": LIVE_URL + "?utm=x"})

    assert again.status_code == 409
    assert again.json()["code"] == "already_captured"
    assert again.json()["funda_id"] == "80907644"
    assert len(listing_provider.calls) == 1
    assert len(client.get("/api/listings").json()) == 1


def test_refetch_adds_a_snapshot_and_keeps_the_old_one(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})
    listing_provider.listings[LIVE_URL] = live_listing(
        raw_status="Verkocht", asking_price=570000
    )

    response = client.post("/api/listings/80907644/refetch")

    assert response.status_code == 200
    snapshots = response.json()["snapshots"]
    assert [s["asking_price"] for s in snapshots] == [570000, 595000]
    assert [s["raw_status"] for s in snapshots] == ["Verkocht", "Beschikbaar"]


def test_refetch_of_unknown_listing_is_not_found(client):
    assert client.post("/api/listings/12345678/refetch").status_code == 404


def test_refetch_failure_keeps_existing_snapshots(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})
    listing_provider.listings[LIVE_URL] = ProviderBlocked()

    response = client.post("/api/listings/80907644/refetch")

    assert response.status_code == 502
    assert len(client.get("/api/listings").json()[0]["snapshots"]) == 1


def test_unexpected_listing_error_is_reported_as_provider_error(client, listing_provider):
    listing_provider.listings[LIVE_URL] = ListingError()

    response = client.post("/api/listings", json={"url": LIVE_URL})

    assert response.status_code == 502
    assert response.json()["code"] == "provider_error"


def test_listing_without_media_or_description_is_captured(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing(
        photo_urls=(), brochure_url=None, description=None, price_history=()
    )

    response = client.post("/api/listings", json={"url": LIVE_URL})

    assert response.status_code == 201
    snapshot = response.json()["snapshots"][0]
    assert snapshot["photo_urls"] == []
    assert snapshot["description"] is None
