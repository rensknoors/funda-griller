from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

FORM = {
    "url": LIVE_URL,
    "raw_status": "Beschikbaar",
    "address": "Buchterweg 15",
    "city": "Holtum",
    "asking_price": "595000",
    "living_area": "152",
    "plot_area": "410",
    "rooms": "6",
    "bedrooms": "4",
    "construction_year": "1931",
    "energy_label": "B",
    "heating": "Warmtepomp",
    "description": "Vrijstaande woning met garage.",
}


def enter(client, data=None, files=None):
    return client.post("/api/listings/manual", data=data or FORM, files=files)


def test_manual_entry_is_stored_as_a_normal_snapshot_without_calling_the_provider(
    client, listing_provider
):
    response = enter(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["funda_id"] == "80907644"
    snapshot = body["snapshots"][0]
    assert (snapshot["address"], snapshot["city"]) == ("Buchterweg 15", "Holtum")
    assert snapshot["asking_price"] == 595000
    assert snapshot["living_area"] == 152
    assert snapshot["construction_year"] == 1931
    assert snapshot["raw_status"] == "Beschikbaar"
    assert snapshot["status"] == "available"
    assert snapshot["entry"] == "manual"
    assert listing_provider.calls == []
    assert [item["funda_id"] for item in client.get("/api/listings").json()] == ["80907644"]


def test_uploaded_photos_are_stored_and_served_from_the_snapshot(client):
    files = [
        ("photos", ("voorgevel.jpg", b"jpeg-bytes-1", "image/jpeg")),
        ("photos", ("keuken.PNG", b"png-bytes-2", "image/png")),
    ]

    snapshot = enter(client, files=files).json()["snapshots"][0]

    assert len(snapshot["photo_urls"]) == 2
    served = [client.get(url) for url in snapshot["photo_urls"]]
    assert [r.status_code for r in served] == [200, 200]
    assert [r.content for r in served] == [b"jpeg-bytes-1", b"png-bytes-2"]


def test_non_image_upload_is_rejected_and_nothing_is_stored(client):
    files = [("photos", ("vragenlijst.pdf", b"%PDF", "application/pdf"))]

    response = enter(client, files=files)

    assert response.status_code == 422
    assert response.json()["code"] == "not_an_image"
    assert client.get("/api/listings").json() == []


def test_unknown_photo_is_not_found(client):
    enter(client)

    assert client.get("/api/listings/80907644/photos/missing.jpg").status_code == 404
    assert client.get("/api/listings/80907644/photos/..%2F..%2Ftest.sqlite").status_code == 404


def test_blank_optional_fields_are_left_empty(client):
    form = {"url": LIVE_URL, "raw_status": "Beschikbaar", "address": "Buchterweg 15"}
    blanks = {key: "" for key in FORM if key not in form}

    response = enter(client, data={**form, **blanks})

    assert response.status_code == 201, response.text
    snapshot = response.json()["snapshots"][0]
    assert snapshot["asking_price"] is None
    assert snapshot["city"] is None
    assert snapshot["photo_urls"] == []


def test_status_is_required(client):
    response = enter(client, data={**FORM, "raw_status": ""})

    assert response.status_code == 422
    assert client.get("/api/listings").json() == []


def test_manual_entry_for_a_bad_url_is_rejected(client):
    response = enter(client, data={**FORM, "url": "https://example.com/huis/1"})

    assert response.status_code == 400
    assert response.json()["code"] == "bad_url"


def test_manual_entry_for_a_captured_listing_is_a_duplicate(client):
    enter(client)

    again = enter(client)

    assert again.status_code == 409
    assert again.json() == {"code": "already_captured", "funda_id": "80907644"}
    assert len(client.get("/api/listings").json()[0]["snapshots"]) == 1


def test_case_is_built_from_a_manual_entry_like_any_other_listing(client):
    snapshot = enter(client).json()["snapshots"][0]
    client.put("/api/buyer-profile", json=typical_profile())

    case = client.get("/api/listings/80907644/case").json()

    assert case["built_from"] == {"snapshot_id": snapshot["id"], "profile_version": 1, "flag_rules_version": 3, "observation_run": None}
    facts = {fact["key"]: fact for fact in case["facts"]}
    assert facts["asking_price"]["value"] == 595000
    assert {fact["provenance"] for fact in facts.values()} == {"listing"}
    assert case["affordability"]["headroom"] == 109_519


def test_refetch_after_manual_entry_uses_the_provider(client, listing_provider):
    enter(client)
    listing_provider.listings[LIVE_URL] = live_listing(asking_price=570000)

    snapshots = client.post("/api/listings/80907644/refetch").json()["snapshots"]

    assert [(s["entry"], s["asking_price"]) for s in snapshots] == [
        ("fetched", 570000),
        ("manual", 595000),
    ]
