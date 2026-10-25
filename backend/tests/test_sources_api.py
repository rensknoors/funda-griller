from app.ports import SourceFact, SourceSkipped
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import high_equity_profile

CAPTURED_AT = "2026-10-24T12:00:00+00:00"


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    return client.post("/api/listings", json={"url": LIVE_URL}).json()


def read_case(client):
    return client.get("/api/listings/80907644/case").json()


def source_facts(case, source):
    return [f for f in case["facts"] if f["provenance"] == "source" and f["source"] == source]


def test_case_shows_the_official_energielabel_with_its_fetch_date(
    client, listing_provider, source_clients
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="C")]
    capture(client, listing_provider)

    [fact] = source_facts(read_case(client), "energielabel")

    assert fact["key"] == "energy_label"
    assert fact["value"] == "C"
    assert fact["trust"] == "official"
    assert fact["fetched_at"] == CAPTURED_AT
    assert fact["stale"] is False


def test_case_states_whether_the_listing_energielabel_matches_the_register(
    client, listing_provider, source_clients
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="C")]
    capture(client, listing_provider, energy_label="B")

    check = read_case(client)["metrics"]["energy_label_check"]

    assert check == {"listing": "B", "register": "C", "matches": False, "provenance": "computed", "computed_at": CAPTURED_AT}


def test_matching_energielabels_are_reported_as_matching(client, listing_provider, source_clients):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="a+++")]
    capture(client, listing_provider, energy_label="A+++")

    assert read_case(client)["metrics"]["energy_label_check"]["matches"] is True


def test_no_energielabel_check_without_a_register_label(client, listing_provider):
    capture(client, listing_provider, energy_label="B")

    assert read_case(client)["metrics"]["energy_label_check"] is None


def test_borrowing_capacity_uses_the_register_label_over_the_listing_claim(
    client, listing_provider, source_clients
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="A+++")]
    client.put("/api/buyer-profile", json=high_equity_profile())
    capture(client, listing_provider, energy_label="E")

    affordability = read_case(client)["affordability"]

    assert affordability["energy_label_bonus"] == 25_000
    assert affordability["max_mortgage"] == 304_422


WOZ_HISTORY = [
    SourceFact(name="woz_value", value=371_000, as_of="2024-01-01"),
    SourceFact(name="woz_value", value=392_000, as_of="2025-01-01"),
]


def test_woz_values_over_time_are_labelled_third_party(client, listing_provider, source_clients):
    source_clients["woz"].facts = WOZ_HISTORY
    capture(client, listing_provider)

    woz = source_facts(read_case(client), "woz")

    assert [(f["as_of"], f["value"]) for f in woz] == [("2024-01-01", 371_000), ("2025-01-01", 392_000)]
    assert {f["trust"] for f in woz} == {"third_party"}
    assert {f["fetched_at"] for f in woz} == {CAPTURED_AT}


def test_asking_price_is_compared_to_the_latest_woz_value(client, listing_provider, source_clients):
    source_clients["woz"].facts = list(reversed(WOZ_HISTORY))
    capture(client, listing_provider, asking_price=490_000)

    metric = read_case(client)["metrics"]["asking_vs_woz"]

    assert metric == {
        "asking_price": 490_000,
        "woz_value": 392_000,
        "woz_as_of": "2025-01-01",
        "difference": 98_000,
        "percent": 25.0,
        "provenance": "computed",
        "computed_at": CAPTURED_AT,
    }


def test_no_asking_vs_woz_without_woz_values(client, listing_provider):
    capture(client, listing_provider)

    assert read_case(client)["metrics"]["asking_vs_woz"] is None


def test_source_facts_turn_stale_after_their_time_to_live_and_stay_visible(
    client, listing_provider, source_clients, settings, clock
):
    settings.source_ttl_days = {"energielabel": 365, "woz": 30}
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="C")]
    source_clients["woz"].facts = WOZ_HISTORY
    capture(client, listing_provider)

    clock.advance(days=30)
    case = read_case(client)
    assert {f["stale"] for f in source_facts(case, "woz")} == {False}

    clock.advance(days=1)
    case = read_case(client)
    woz = source_facts(case, "woz")
    assert [f["value"] for f in woz] == [371_000, 392_000]
    assert {(f["stale"], f["ttl_days"], f["fetched_at"]) for f in woz} == {(True, 30, CAPTURED_AT)}
    [label] = source_facts(case, "energielabel")
    assert label["stale"] is False


def test_reading_a_case_never_refetches_sources(client, listing_provider, source_clients, clock):
    capture(client, listing_provider)
    clock.advance(days=400)

    read_case(client)

    assert len(source_clients["energielabel"].calls) == 1
    assert len(listing_provider.calls) == 1


def sources_by_name(case):
    return {s["source"]: s for s in case["sources"]}


def test_a_failing_source_leaves_the_case_intact_and_is_listed_as_failed(
    client, listing_provider, source_clients
):
    source_clients["energielabel"].error = ConnectionError("register down")
    source_clients["woz"].facts = WOZ_HISTORY
    source_clients["noise"].error = SourceSkipped("no_coordinates")

    created = capture(client, listing_provider)
    response = client.get("/api/listings/80907644/case")

    assert created["funda_id"] == "80907644"
    assert response.status_code == 200
    case = response.json()
    sources = sources_by_name(case)
    assert sources["energielabel"]["status"] == "failed"
    assert sources["woz"]["status"] == "succeeded"
    assert sources["noise"] == {
        "source": "noise",
        "status": "skipped",
        "reason": "no_coordinates",
        "attempted_at": CAPTURED_AT,
        "trust": "official",
    }
    assert source_facts(case, "energielabel") == []
    assert len(source_facts(case, "woz")) == 2
    assert {f["key"] for f in case["facts"] if f["provenance"] == "listing"} >= {"asking_price"}
    assert case["metrics"]["energy_label_check"] is None


def test_refetching_one_source_refreshes_only_that_source(
    client, listing_provider, source_clients, clock
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="C")]
    source_clients["woz"].facts = WOZ_HISTORY
    capture(client, listing_provider)
    clock.advance(days=400)
    source_clients["woz"].facts = [*WOZ_HISTORY, SourceFact("woz_value", 405_000, "2026-01-01")]

    response = client.post("/api/listings/80907644/sources/woz/refetch")

    assert response.status_code == 200
    case = response.json()
    woz = source_facts(case, "woz")
    assert [f["value"] for f in woz] == [371_000, 392_000, 405_000]
    assert {(f["stale"], f["fetched_at"]) for f in woz} == {(False, clock().isoformat())}
    [label] = source_facts(case, "energielabel")
    assert label["stale"] is True
    assert len(source_clients["energielabel"].calls) == 1
    assert len(listing_provider.calls) == 1
    assert case == read_case(client)


def test_a_failed_refetch_keeps_the_last_good_facts_and_reports_the_failure(
    client, listing_provider, source_clients, clock
):
    source_clients["woz"].facts = WOZ_HISTORY
    capture(client, listing_provider)
    clock.advance(days=400)
    source_clients["woz"].error = TimeoutError()

    case = client.post("/api/listings/80907644/sources/woz/refetch").json()

    assert sources_by_name(case)["woz"]["status"] == "failed"
    assert sources_by_name(case)["woz"]["attempted_at"] == clock().isoformat()
    woz = source_facts(case, "woz")
    assert {(f["stale"], f["fetched_at"]) for f in woz} == {(True, CAPTURED_AT)}


def test_refetching_an_unknown_source_or_listing_is_not_found(client, listing_provider):
    capture(client, listing_provider)

    assert client.post("/api/listings/80907644/sources/kadaster/refetch").status_code == 404
    assert client.post("/api/listings/1/sources/woz/refetch").status_code == 404


def test_refetching_the_listing_refetches_every_automatic_source(
    client, listing_provider, source_clients, clock
):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="C")]
    capture(client, listing_provider)
    clock.advance(days=400)

    client.post("/api/listings/80907644/refetch")

    # Comparables are fetched only on their own request (see test_comparables_api).
    assert {len(c.calls) for n, c in source_clients.items() if n != "comparables"} == {2}
    [label] = source_facts(read_case(client), "energielabel")
    assert label["stale"] is False
