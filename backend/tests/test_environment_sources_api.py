"""Flood and soil risk (Klimaateffectatlas) and noise (RIVM) Sources, through the HTTP API."""

from app.ports import SourceFact
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

CAPTURED_AT = "2026-10-24T12:00:00+00:00"

FLOOD_SOIL = [
    SourceFact(name="flood_depth_m", value=0.88, as_of="2026-01-28"),
    SourceFact(name="subsidence_mm_per_year", value=1.5, as_of="2026-06-23"),
    SourceFact(name="pile_rot_risk_pct", value=2.1),
]
NOISE = [
    SourceFact(name="lden_all_sources_db", value=57, as_of="2020"),
    SourceFact(name="lden_road_db", value=55, as_of="2020"),
]


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    client.post("/api/listings", json={"url": LIVE_URL})


def read_case(client):
    return client.get("/api/listings/80907644/case").json()


def source_facts(case, source):
    return {
        f["key"]: f for f in case["facts"] if f["provenance"] == "source" and f["source"] == source
    }


def test_flood_and_soil_risk_facts_appear_in_the_case_with_their_fetch_date(
    client, listing_provider, source_clients
):
    source_clients["flood_soil"].facts = FLOOD_SOIL
    capture(client, listing_provider)

    facts = source_facts(read_case(client), "flood_soil")

    assert {key: f["value"] for key, f in facts.items()} == {
        "flood_depth_m": 0.88,
        "subsidence_mm_per_year": 1.5,
        "pile_rot_risk_pct": 2.1,
    }
    assert {(f["fetched_at"], f["stale"], f["trust"]) for f in facts.values()} == {
        (CAPTURED_AT, False, "official")
    }


def test_noise_levels_appear_in_the_case(client, listing_provider, source_clients):
    source_clients["noise"].facts = NOISE
    capture(client, listing_provider)

    facts = source_facts(read_case(client), "noise")

    assert {key: (f["value"], f["as_of"]) for key, f in facts.items()} == {
        "lden_all_sources_db": (57, "2020"),
        "lden_road_db": (55, "2020"),
    }
    assert {(f["fetched_at"], f["trust"]) for f in facts.values()} == {(CAPTURED_AT, "official")}


def flags_by_rule(case):
    return {flag["rule_id"]: flag for flag in case["flags"]}


def evidence(flag):
    return {item["key"]: item["value"] for item in flag["evidence"]}


def test_noise_above_the_threshold_is_a_con_citing_the_noise_level(
    client, listing_provider, source_clients
):
    source_clients["noise"].facts = [SourceFact(name="lden_all_sources_db", value=64, as_of="2020")]
    capture(client, listing_provider)

    flag = flags_by_rule(read_case(client))["noise_high"]

    assert flag["class"] == "con"
    assert flag["rule_version"] == 1
    assert evidence(flag) == {"lden_all_sources_db": 64, "threshold": 60}
    [noise] = [item for item in flag["evidence"] if item["key"] == "lden_all_sources_db"]
    assert (noise["source"], noise["fetched_at"]) == ("noise", CAPTURED_AT)


def test_noise_at_the_threshold_raises_no_flag(client, listing_provider, source_clients):
    source_clients["noise"].facts = [SourceFact(name="lden_all_sources_db", value=60, as_of="2020")]
    capture(client, listing_provider)

    assert "noise_high" not in flags_by_rule(read_case(client))


def test_deep_flooding_in_the_small_chance_scenario_is_a_risk(
    client, listing_provider, source_clients
):
    source_clients["flood_soil"].facts = [
        SourceFact(name="flood_depth_m", value=1.2, as_of="2026-01-28")
    ]
    capture(client, listing_provider)

    flag = flags_by_rule(read_case(client))["flood_depth_high"]

    assert flag["class"] == "risk"
    assert evidence(flag) == {"flood_depth_m": 1.2, "threshold": 0.5}


def test_low_foundation_and_subsidence_risk_raises_no_flag(client, listing_provider, source_clients):
    source_clients["flood_soil"].facts = FLOOD_SOIL
    capture(client, listing_provider)

    flags = flags_by_rule(read_case(client))

    assert flags.keys().isdisjoint({"pile_rot_risk_high", "subsidence_significant"})


def test_foundation_and_subsidence_risks_above_their_thresholds_are_risks(
    client, listing_provider, source_clients
):
    source_clients["flood_soil"].facts = [
        SourceFact(name="subsidence_mm_per_year", value=7.3, as_of="2026-06-23"),
        SourceFact(name="pile_rot_risk_pct", value=28.0),
    ]
    capture(client, listing_provider)

    flags = flags_by_rule(read_case(client))

    assert flags["pile_rot_risk_high"]["class"] == "risk"
    assert evidence(flags["pile_rot_risk_high"]) == {"pile_rot_risk_pct": 28.0, "threshold": 6}
    assert flags["subsidence_significant"]["class"] == "risk"
    assert evidence(flags["subsidence_significant"]) == {
        "subsidence_mm_per_year": 7.3,
        "threshold": 5,
    }


def test_a_deal_breaker_naming_flood_risk_forces_hard_no(client, listing_provider, source_clients):
    source_clients["flood_soil"].facts = [
        SourceFact(name="flood_depth_m", value=1.2, as_of="2026-01-28")
    ]
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Overstroming"]})
    capture(client, listing_provider)

    hard_no = read_case(client)["hard_no"]

    assert hard_no == {"tier": "hard_no", "deal_breaker": "Overstroming", "flag_id": "flood_depth_high"}


def sources_by_name(case):
    return {s["source"]: s for s in case["sources"]}


def test_flood_soil_and_noise_facts_turn_stale_and_refetch_per_source(
    client, listing_provider, source_clients, settings, clock
):
    settings.source_ttl_days = {"flood_soil": 365, "noise": 30}
    source_clients["flood_soil"].facts = FLOOD_SOIL
    source_clients["noise"].facts = NOISE
    capture(client, listing_provider)
    clock.advance(days=31)

    case = read_case(client)
    assert {f["stale"] for f in source_facts(case, "noise").values()} == {True}
    assert {f["stale"] for f in source_facts(case, "flood_soil").values()} == {False}

    source_clients["noise"].facts = [SourceFact(name="lden_all_sources_db", value=62, as_of="2022")]
    refetched = client.post("/api/listings/80907644/sources/noise/refetch").json()

    [noise] = source_facts(refetched, "noise").values()
    assert (noise["value"], noise["stale"], noise["fetched_at"]) == (62, False, clock().isoformat())
    assert "noise_high" in flags_by_rule(refetched)
    assert len(source_clients["flood_soil"].calls) == 1


def test_a_failing_flood_soil_source_leaves_noise_and_the_case_intact(
    client, listing_provider, source_clients
):
    source_clients["flood_soil"].error = TimeoutError()
    source_clients["noise"].facts = NOISE
    capture(client, listing_provider)

    response = client.get("/api/listings/80907644/case")

    assert response.status_code == 200
    case = response.json()
    assert sources_by_name(case)["flood_soil"]["status"] == "failed"
    assert sources_by_name(case)["noise"]["status"] == "succeeded"
    assert source_facts(case, "flood_soil") == {}
    assert len(source_facts(case, "noise")) == 2
    assert flags_by_rule(case).keys().isdisjoint({"flood_depth_high", "pile_rot_risk_high"})
