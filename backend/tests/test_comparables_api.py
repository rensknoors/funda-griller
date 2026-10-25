"""Comparables: nearby Listings fetched on request, the asking price set against them, and the
Walk-away Maximum grounded in them as well as in affordability."""

from app.ports import SourceFact

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

CASE = "/api/listings/80907644/case"
FETCH_COMPARABLES = "/api/listings/80907644/sources/comparables/refetch"
VERDICT = "/api/listings/80907644/verdict"
NOW = "2026-10-24T12:00:00+00:00"

# The typical household can pay at most 704_519 for the live Listing (asking 595_000, 152 m²).
AFFORDABLE_MAXIMUM = 704_519


def comparable(funda_id, asking_price, living_area, recently_sold=True):
    return SourceFact(
        "comparable",
        {
            "funda_id": funda_id,
            "address": f"Dorpsstraat {funda_id}",
            "city": "Holtum",
            "asking_price": asking_price,
            "living_area": living_area,
            "raw_status": "Verkocht" if recently_sold else "Beschikbaar",
            "recently_sold": recently_sold,
            "url": f"https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat/{funda_id}/",
        },
    )


# Price per m²: 4000, 4000, 4200, 3600 -> median 4000, so 152 m² is worth 608_000 by comparables.
SEVERAL = [
    comparable("101", 500_000, 125),
    comparable("102", 480_000, 120),
    comparable("103", 630_000, 150),
    comparable("104", 360_000, 100, recently_sold=False),
]


def capture(client, listing_provider):
    listing_provider.listings[LIVE_URL] = live_listing()
    client.post("/api/listings", json={"url": LIVE_URL})


def with_comparables(client, listing_provider, source_clients, facts):
    capture(client, listing_provider)
    source_clients["comparables"].facts = facts
    return client.post(FETCH_COMPARABLES)


def bid(walk_away):
    return {
        "tier": "consider",
        "summary": "Prima woning.",
        "reasoning": "Past bij de wensen.",
        "cited_flags": [],
        "bid_advice": {
            "opening_bid": 580_000,
            "walk_away_maximum": walk_away,
            "conditions": ["Financieringsvoorbehoud"],
        },
    }


def test_comparables_are_not_fetched_until_the_user_asks(client, listing_provider, source_clients):
    capture(client, listing_provider)

    case = client.get(CASE).json()

    assert source_clients["comparables"].calls == []
    assert next(s for s in case["sources"] if s["source"] == "comparables")["reason"] == "not_fetched"
    assert case["metrics"]["asking_vs_comparables"]["coverage"] == "not_fetched"


def test_refetching_the_listing_does_not_fetch_comparables(client, listing_provider, source_clients):
    capture(client, listing_provider)

    client.post("/api/listings/80907644/refetch")

    assert source_clients["comparables"].calls == []


def test_asking_price_is_compared_to_several_comparables_per_square_metre(
    client, listing_provider, source_clients
):
    case = with_comparables(client, listing_provider, source_clients, SEVERAL).json()

    assert len(source_clients["comparables"].calls) == 1
    metric = case["metrics"]["asking_vs_comparables"]
    assert metric == {
        "coverage": "sufficient",
        "count": 4,
        "min_count": 3,
        "price_per_m2": 3914,
        "median_price_per_m2": 4000,
        "percent": -2.1,
        "comparables_value": 608_000,
        "provenance": "computed",
        "computed_at": NOW,
    }
    listed = [f["value"]["funda_id"] for f in case["facts"] if f.get("source") == "comparables"]
    assert listed == ["101", "102", "103", "104"]


def test_a_single_comparable_is_stated_as_thin(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, [comparable("101", 500_000, 125)]).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert metric["coverage"] == "thin"
    assert metric["count"] == 1
    assert metric["percent"] == -2.1


def test_no_comparables_is_stated_rather_than_hidden(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, []).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert metric["coverage"] == "none"
    assert metric["count"] == 0
    assert metric["percent"] is None
    assert metric["comparables_value"] is None


def test_comparables_without_price_or_area_do_not_count(client, listing_provider, source_clients):
    facts = SEVERAL[:2] + [comparable("105", None, 90), comparable("106", 400_000, None)]

    case = with_comparables(client, listing_provider, source_clients, facts).json()

    assert case["metrics"]["asking_vs_comparables"]["count"] == 2
    assert case["metrics"]["asking_vs_comparables"]["coverage"] == "thin"


def test_the_comparison_row_shows_asking_vs_comparables(client, listing_provider, source_clients):
    with_comparables(client, listing_provider, source_clients, SEVERAL)

    [row] = client.get("/api/listings").json()

    assert row["comparison"]["asking_vs_comparables_percent"] == -2.1


def test_walk_away_maximum_above_what_comparables_support_is_rejected(
    client, listing_provider, source_clients, llm_client
):
    with_comparables(client, listing_provider, source_clients, SEVERAL)
    client.put("/api/buyer-profile", json=typical_profile())
    # Comparables put the house at 608_000; at most 10% above that is 668_800.
    llm_client.verdict = bid(680_000)

    rejected = client.post(VERDICT)

    assert rejected.status_code == 502
    assert rejected.json()["problems"] == ["walk_away_maximum_above_comparables"]
    assert client.get(VERDICT).json()["verdicts"] == []


def test_walk_away_maximum_within_comparables_and_affordability_shows_both_inputs(
    client, listing_provider, source_clients, llm_client
):
    with_comparables(client, listing_provider, source_clients, SEVERAL)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid(650_000)

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == 650_000
    assert advice["affordable_maximum"] == AFFORDABLE_MAXIMUM
    assert advice["comparables"] == {
        "coverage": "sufficient",
        "count": 4,
        "comparables_value": 608_000,
        "maximum": 668_800,
    }
    # The model is told both limits before it answers.
    [(sent_case, _)] = llm_client.rate_calls
    assert sent_case["bid_limits"] == {"affordable_maximum": AFFORDABLE_MAXIMUM, "comparables_maximum": 668_800}


def test_thin_comparables_leave_the_walk_away_maximum_bounded_by_affordability_alone(
    client, listing_provider, source_clients, llm_client
):
    with_comparables(client, listing_provider, source_clients, [comparable("101", 500_000, 125)])
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid(700_000)

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == 700_000
    assert advice["comparables"] == {
        "coverage": "thin",
        "count": 1,
        "comparables_value": 608_000,
        "maximum": None,
    }


def test_walk_away_maximum_never_exceeds_affordability_even_when_comparables_allow_more(
    client, listing_provider, source_clients, llm_client
):
    pricey = [comparable(str(i), 800_000, 150) for i in (101, 102, 103)]
    with_comparables(client, listing_provider, source_clients, pricey)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid(720_000)

    rejected = client.post(VERDICT)

    assert rejected.json()["problems"] == ["walk_away_maximum_above_affordability"]


def test_fetching_comparables_makes_an_earlier_verdict_out_of_date(
    client, listing_provider, source_clients, llm_client
):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid(650_000)
    client.post(VERDICT)

    source_clients["comparables"].facts = SEVERAL
    client.post(FETCH_COMPARABLES)

    state = client.get(VERDICT).json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["case"]


# Price per m² 3000 each: the live Listing asks 595_000 / 152 m² = 3914 per m², 30.5% above.
CHEAPER = [comparable("201", 300_000, 100), comparable("202", 360_000, 120), comparable("203", 450_000, 150)]


def flags_by_rule(case):
    return {flag["rule_id"]: flag for flag in case["flags"]}


def test_asking_far_above_sufficient_comparables_is_a_con(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, CHEAPER).json()

    flag = flags_by_rule(case)["ask_far_above_comparables"]
    assert flag["class"] == "con"
    assert {item["key"]: item["value"] for item in flag["evidence"]} == {
        "asking_vs_comparables_percent": 30.5,
        "threshold": 15,
        "asking_price": 595_000,
    }


def test_thin_comparables_raise_no_overpricing_flag(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, CHEAPER[:2]).json()

    assert "ask_far_above_comparables" not in flags_by_rule(case)


def test_asking_in_line_with_comparables_raises_no_overpricing_flag(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, SEVERAL).json()

    assert "ask_far_above_comparables" not in flags_by_rule(case)
