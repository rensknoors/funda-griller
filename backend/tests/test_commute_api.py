"""Commute Source and Flag, through the HTTP API: travel time from the Listing to each Buyer
Profile commute destination, by car and by bike, against the destination's `max_minutes`."""

import pytest

from app.ports import SourceFailed, SourceSkipped
from tests.fakes import FakeGeocoder, FakeTravelTimeRouter
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

CASE = "/api/listings/80907644/case"
CAPTURED_AT = "2026-10-24T12:00:00+00:00"
OFFICE = "Kantoorlaan 1, Eindhoven"
OFFICE_AT = (51.44, 5.47)
SCHOOL = "Schoolstraat 3, Sittard"
SCHOOL_AT = (51.0, 5.87)


@pytest.fixture
def geocoder():
    found = FakeGeocoder()
    found.places = {OFFICE: OFFICE_AT, SCHOOL: SCHOOL_AT}
    return found


@pytest.fixture
def router():
    return FakeTravelTimeRouter()


def commuting(*destinations, deal_breakers=()):
    profile = typical_profile()
    profile["commute_destinations"] = [
        {"label": label, "address": address, "max_minutes": max_minutes}
        for label, address, max_minutes in destinations
    ]
    profile["deal_breakers"] = list(deal_breakers)
    return profile


def capture(client, listing_provider, profile, **listing_overrides):
    client.put("/api/buyer-profile", json=profile)
    listing_provider.listings[LIVE_URL] = live_listing(**listing_overrides)
    client.post("/api/listings", json={"url": LIVE_URL})
    return client.get(CASE).json()


def commute_facts(case):
    return [f for f in case["facts"] if f["provenance"] == "source" and f["source"] == "commute"]


def commute_status(case):
    return next(s for s in case["sources"] if s["source"] == "commute")


def commute_flags(case):
    return [flag for flag in case["flags"] if flag["rule_id"] == "commute_too_long"]


def test_travel_time_within_the_limit_is_a_fact_and_raises_no_flag(client, listing_provider, router):
    router.minutes = {("car", OFFICE_AT): 38.4, ("bike", OFFICE_AT): 95.0}

    case = capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))

    [fact] = commute_facts(case)
    assert fact["key"] == "travel_minutes"
    assert fact["value"] == {
        "destination": "Werk",
        "minutes": 38,
        "mode": "car",
        "minutes_by_mode": {"car": 38, "bike": 95},
        "public_transport": False,
    }
    assert (fact["fetched_at"], fact["stale"]) == (CAPTURED_AT, False)
    assert commute_status(case)["status"] == "succeeded"
    assert commute_flags(case) == []


def test_each_destination_over_its_limit_is_a_con_citing_travel_time_threshold_and_modes(
    client, listing_provider, router
):
    router.minutes = {
        ("car", OFFICE_AT): 52.0,
        ("bike", OFFICE_AT): 140.0,
        ("car", SCHOOL_AT): 12.0,
        ("bike", SCHOOL_AT): 25.0,
    }

    case = capture(
        client, listing_provider, commuting(("Werk", OFFICE, 45), ("School", SCHOOL, 20))
    )

    [flag] = commute_flags(case)
    assert flag["id"] == "commute_too_long:Werk"
    assert flag["class"] == "con"
    assert flag["title"] == "Reistijd boven je maximum: Werk"
    travel, limit = flag["evidence"]
    assert (travel["key"], travel["value"], travel["provenance"], travel["fetched_at"]) == (
        "travel_minutes",
        52,
        "source",
        CAPTURED_AT,
    )
    # The modes are stated: the faster of car and bike counts, public transport is not included.
    assert travel["commute"] == {
        "destination": "Werk",
        "minutes": 52,
        "mode": "car",
        "minutes_by_mode": {"car": 52, "bike": 140},
        "public_transport": False,
    }
    assert (limit["key"], limit["value"], limit["provenance"]) == ("max_minutes", 45, "buyer_profile")
    assert limit["computed_at"] == CAPTURED_AT


def test_a_destination_without_a_limit_raises_nothing(client, listing_provider, router):
    router.minutes = {("car", OFFICE_AT): 90.0}

    case = capture(client, listing_provider, commuting(("Werk", OFFICE, None)))

    assert commute_facts(case)[0]["value"]["minutes"] == 90
    assert commute_flags(case) == []


def test_a_deal_breaker_naming_the_commute_is_hit_by_it(client, listing_provider, router):
    router.minutes = {("car", OFFICE_AT): 52.0}

    case = capture(
        client,
        listing_provider,
        commuting(("Werk", OFFICE, 45), deal_breakers=["Te ver van werk"]),
    )

    assert case["hard_no"] == {
        "tier": "hard_no",
        "deal_breaker": "Te ver van werk",
        "flag_id": "commute_too_long:Werk",
    }


def test_no_coordinates_skips_the_commute_source(client, listing_provider, router):
    case = capture(
        client, listing_provider, commuting(("Werk", OFFICE, 45)), latitude=None, longitude=None
    )

    assert (commute_status(case)["status"], commute_status(case)["reason"]) == ("skipped", "no_coordinates")
    assert commute_facts(case) == []
    assert router.calls == []


def test_no_commute_destinations_skips_the_commute_source(client, listing_provider, geocoder):
    case = capture(client, listing_provider, commuting())

    assert (commute_status(case)["status"], commute_status(case)["reason"]) == ("skipped", "no_destinations")
    assert geocoder.calls == []


def test_the_routing_service_failing_fails_the_source_and_the_case_still_builds(
    client, listing_provider, router
):
    router.error = SourceFailed("http_503")
    client.put("/api/buyer-profile", json=commuting(("Werk", OFFICE, 45)))
    listing_provider.listings[LIVE_URL] = live_listing()

    captured = client.post("/api/listings", json={"url": LIVE_URL})
    response = client.get(CASE)

    assert captured.status_code == 201
    assert response.status_code == 200
    case = response.json()
    assert (commute_status(case)["status"], commute_status(case)["reason"]) == ("failed", "http_503")
    assert commute_flags(case) == []


def test_a_destination_address_is_geocoded_once_and_never_reaches_the_case_or_the_model(
    client, listing_provider, geocoder, router, llm_client
):
    router.minutes = {("car", OFFICE_AT): 30.0}
    case = capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))
    client.post("/api/listings/80907644/sources/commute/refetch")
    client.post("/api/listings/80907644/verdict")

    assert geocoder.calls == [OFFICE]
    assert {origin for origin, _, _ in router.calls} == {(51.0, 5.8)}
    assert {tuple(destinations) for _, destinations, _ in router.calls} == {(OFFICE_AT,)}
    [(sent_case, sent_profile)] = llm_client.rate_calls
    for shared in (case, sent_case, sent_profile):
        assert "Kantoorlaan" not in repr(shared)
        assert "address_ref" not in repr(shared)


def test_an_address_the_geocoder_does_not_find_fails_the_source(client, listing_provider):
    case = capture(client, listing_provider, commuting(("Werk", "Nergensweg 1, Nergens", 45)))

    assert (commute_status(case)["status"], commute_status(case)["reason"]) == (
        "failed",
        "destination_not_found",
    )


def test_a_destination_not_found_or_not_routable_is_shown_as_unknown_beside_the_others(
    client, listing_provider, router
):
    router.minutes = {("car", OFFICE_AT): 52.0}
    lost = "Nergensweg 1, Nergens"

    case = capture(
        client,
        listing_provider,
        commuting(("Werk", OFFICE, 45), ("Sport", lost, 20), ("School", SCHOOL, 20)),
    )

    assert commute_status(case)["status"] == "succeeded"
    assert {f["value"]["destination"]: f["value"] for f in commute_facts(case)} == {
        "Werk": {
            "destination": "Werk",
            "minutes": 52,
            "mode": "car",
            "minutes_by_mode": {"car": 52},
            "public_transport": False,
        },
        "Sport": {"destination": "Sport", "minutes": None, "unavailable": "destination_not_found"},
        "School": {"destination": "School", "minutes": None, "unavailable": "no_route"},
    }
    assert [flag["id"] for flag in commute_flags(case)] == ["commute_too_long:Werk"]


def test_a_changed_address_is_not_judged_with_the_old_travel_time_until_it_is_refetched(
    client, listing_provider, router
):
    router.minutes = {("car", OFFICE_AT): 52.0, ("car", SCHOOL_AT): 30.0}
    capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))

    client.put("/api/buyer-profile", json=commuting(("Werk", SCHOOL, 45)))
    moved = client.get(CASE).json()

    assert commute_facts(moved) == []
    assert commute_flags(moved) == []
    assert moved["metrics"]["commute_coverage"]["not_fetched"] == ["Werk"]

    client.post("/api/listings/80907644/sources/commute/refetch")
    refetched = client.get(CASE).json()

    assert [f["value"]["minutes"] for f in commute_facts(refetched)] == [30]
    assert refetched["metrics"]["commute_coverage"] is None


def test_a_destination_added_after_the_fetch_is_shown_as_not_fetched(client, listing_provider, router):
    router.minutes = {("car", OFFICE_AT): 30.0}
    capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))

    client.put("/api/buyer-profile", json=commuting(("Werk", OFFICE, 45), ("School", SCHOOL, 20)))
    case = client.get(CASE).json()

    assert [f["value"]["destination"] for f in commute_facts(case)] == ["Werk"]
    assert case["metrics"]["commute_coverage"]["not_fetched"] == ["School"]


def test_a_removed_destination_leaves_the_case(client, listing_provider, router):
    router.minutes = {("car", OFFICE_AT): 52.0, ("car", SCHOOL_AT): 30.0}
    capture(client, listing_provider, commuting(("Werk", OFFICE, 45), ("School", SCHOOL, 40)))

    client.put("/api/buyer-profile", json=commuting(("School", SCHOOL, 40)))
    case = client.get(CASE).json()

    assert [f["value"]["destination"] for f in commute_facts(case)] == ["School"]
    assert commute_flags(case) == []
    assert case["metrics"]["commute_coverage"] is None


def test_commute_facts_turn_stale_after_their_time_to_live(client, listing_provider, router, clock):
    router.minutes = {("car", OFFICE_AT): 30.0}
    capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))

    clock.advance(days=180)
    assert {f["stale"] for f in commute_facts(client.get(CASE).json())} == {False}
    clock.advance(days=1)
    [fact] = commute_facts(client.get(CASE).json())

    assert (fact["stale"], fact["ttl_days"], fact["fetched_at"]) == (True, 180, CAPTURED_AT)


def test_without_a_routing_key_the_source_is_skipped_before_any_address_leaves_the_machine(
    client, listing_provider, geocoder, router
):
    router.unavailable = SourceSkipped("no_api_key")

    case = capture(client, listing_provider, commuting(("Werk", OFFICE, 45)))

    assert (commute_status(case)["status"], commute_status(case)["reason"]) == ("skipped", "no_api_key")
    assert geocoder.calls == []
