"""Comparables: nearby Listings fetched on request, the asking price set against them, and the
Walk-away Maximum grounded in them as well as in affordability."""

import pytest

from app.ports import SourceFact

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import well_off_profile

CASE = "/api/listings/80907644/case"
FETCH_COMPARABLES = "/api/listings/80907644/sources/comparables/refetch"
VERDICT = "/api/listings/80907644/verdict"
NOW = "2026-10-24T12:00:00+00:00"

# The well-off household can pay at most 709_174 for the live Listing (asking 595_000, 152 m²).
AFFORDABLE_MAXIMUM = 709_174

NVM = "NVM, Marktoverzicht Nederland 2e kwartaal 2026 (via openwoning.nl)"


def comparable(funda_id, asking_price, living_area, recently_sold=True, object_type=None, house_type=None):
    return SourceFact(
        "comparable",
        {
            "funda_id": funda_id,
            "address": f"Dorpsstraat {funda_id}",
            "city": "Holtum",
            "asking_price": asking_price,
            "living_area": living_area,
            "raw_status": "Verkocht" if recently_sold else "Beschikbaar",
            "object_type": object_type,
            "house_type": house_type,
            "recently_sold": recently_sold,
            "url": f"https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat/{funda_id}/",
        },
    )


# Price per m²: 4000, 4000, 4200, 3600, 4000 -> median 4000, so 152 m² is worth 608_000 by comparables.
SEVERAL = [
    comparable("101", 500_000, 125),
    comparable("102", 480_000, 120),
    comparable("103", 630_000, 150),
    comparable("104", 360_000, 100, recently_sold=False),
    comparable("107", 440_000, 110),
]


def capture(client, listing_provider, **listing_overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**listing_overrides)
    client.post("/api/listings", json={"url": LIVE_URL})


def with_comparables(client, listing_provider, source_clients, facts, **listing_overrides):
    capture(client, listing_provider, **listing_overrides)
    source_clients["comparables"].facts = facts
    return client.post(FETCH_COMPARABLES)


def bid(opening_bid=580_000, **extra):
    """The model's answer: tier, reasoning, an opening bid and conditions, never a Walk-away Maximum."""
    return {
        "tier": "consider",
        "summary": "Prima woning.",
        "reasoning": "Past bij de wensen.",
        "cited_flags": [],
        "bid_advice": {"opening_bid": opening_bid, "conditions": ["Financieringsvoorbehoud"], **extra},
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
        "count": 5,
        "min_count": 5,
        "matched_on": None,
        "excluded": 0,
        "price_per_m2": 3914,
        "median_price_per_m2": 4000,
        "percent": -2.1,
        "comparables_value": 608_000,
        "provenance": "computed",
        "computed_at": NOW,
    }
    listed = [f["value"]["funda_id"] for f in case["facts"] if f.get("source") == "comparables"]
    assert listed == ["101", "102", "103", "104", "107"]


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


def test_sufficient_comparables_derive_the_walk_away_maximum(client, listing_provider, source_clients, llm_client):
    with_comparables(client, listing_provider, source_clients, SEVERAL)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    # Comparables put the house at 608_000; 10% above that is 668_800, below affordability.
    assert advice["walk_away_maximum"] == 668_800
    assert advice["affordable_maximum"] == AFFORDABLE_MAXIMUM
    assert advice["comparables"] == {
        "coverage": "sufficient",
        "count": 5,
        "comparables_value": 608_000,
        "maximum": 668_800,
    }
    assert advice["derivation"] == {
        "basis": "comparables",
        "renovation_direct": 0,
        "margin": 0.10,
        "margin_source": None,
        "basis_maximum": 668_800,
        "binding": "basis",
        "weakly_grounded": False,
    }
    # The model is told the derived figure before it answers.
    [(sent_case, _)] = llm_client.rate_calls
    assert sent_case["walk_away"]["walk_away_maximum"] == 668_800


def test_affordability_binds_the_walk_away_maximum_when_comparables_would_allow_more(
    client, listing_provider, source_clients, llm_client
):
    # 800_000 for 150 m² each: comparables put the house at 810_667, plus 10% far above affordability.
    pricey = [comparable(str(i), 800_000, 150) for i in (101, 102, 103, 104, 105)]
    with_comparables(client, listing_provider, source_clients, pricey)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == AFFORDABLE_MAXIMUM
    assert advice["derivation"]["basis"] == "comparables"
    assert advice["derivation"]["binding"] == "affordability"
    assert advice["derivation"]["basis_maximum"] > AFFORDABLE_MAXIMUM


@pytest.mark.parametrize(
    ("facts", "coverage"),
    [([comparable("101", 500_000, 125)], "thin"), ([], "none"), (None, "not_fetched")],
)
def test_without_sufficient_comparables_the_walk_away_maximum_rests_weakly_on_the_asking_price(
    client, listing_provider, source_clients, llm_client, facts, coverage
):
    if facts is None:
        capture(client, listing_provider)
    else:
        with_comparables(client, listing_provider, source_clients, facts)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    # Asking 595_000 plus 4,6%, NVM's average overbid for all homes (the Listing's soort woning is
    # unknown); the thin comparables value is not used.
    assert advice["walk_away_maximum"] == 622_370
    assert advice["comparables"]["coverage"] == coverage
    assert advice["comparables"]["maximum"] is None
    assert advice["derivation"] == {
        "basis": "asking_price",
        "renovation_direct": 0,
        "margin": 0.046,
        "margin_source": {"house_type": None, "source": NVM, "period": "2e kwartaal 2026"},
        "basis_maximum": 622_370,
        "binding": "basis",
        "weakly_grounded": True,
    }


def test_with_neither_comparables_nor_an_asking_price_only_affordability_bounds_the_walk_away_maximum(
    client, listing_provider, llm_client
):
    listing_provider.listings[LIVE_URL] = live_listing(asking_price=None)
    client.post("/api/listings", json={"url": LIVE_URL})
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == AFFORDABLE_MAXIMUM
    assert advice["derivation"] == {
        "basis": "affordability",
        "renovation_direct": 0,
        "margin": None,
        "margin_source": None,
        "basis_maximum": None,
        "binding": "affordability",
        "weakly_grounded": True,
    }


@pytest.mark.parametrize(
    ("house_type", "category", "margin", "walk_away"),
    [
        ("Eengezinswoning, tussenwoning", "tussenwoning", 0.059, 630_105),
        ("Eengezinswoning, hoekwoning", "hoekwoning", 0.044, 621_180),
        ("Woonboerderij, 2-onder-1-kapwoning", "twee_onder_een_kap", 0.035, 615_825),
        ("Villa, vrijstaande woning", "vrijstaand", 0.006, 598_570),
        ("Bovenwoning", "appartement", 0.056, 628_320),
    ],
)
def test_the_asking_price_margin_follows_the_soort_woning(
    client, listing_provider, source_clients, llm_client, house_type, category, margin, walk_away
):
    """NVM Q2 2026 average overbid by house type, on an asking price of 595.000."""
    with_comparables(client, listing_provider, source_clients, [], house_type=house_type)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid(opening_bid=590_000)

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == walk_away
    assert advice["derivation"]["margin"] == margin
    assert advice["derivation"]["margin_source"]["house_type"] == category


def test_the_asking_price_margins_come_from_configuration(
    client, listing_provider, source_clients, settings, llm_client, tmp_path
):
    table = tmp_path / "bid_margins.toml"
    table.write_text(settings.bid_margins_path.read_text().replace("all = 0.046", "all = 0.08"))
    settings.bid_margins_path = table
    with_comparables(client, listing_provider, source_clients, [])
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == 642_600


def test_a_walk_away_maximum_from_the_model_is_ignored(client, listing_provider, source_clients, llm_client):
    with_comparables(client, listing_provider, source_clients, SEVERAL)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid(walk_away_maximum=700_000)

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == 668_800


def test_an_opening_bid_above_the_derived_walk_away_maximum_is_rejected(
    client, listing_provider, source_clients, llm_client
):
    with_comparables(client, listing_provider, source_clients, [comparable("101", 500_000, 125)])
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid(opening_bid=630_000)

    rejected = client.post(VERDICT)

    assert rejected.status_code == 502
    assert rejected.json()["problems"] == ["opening_bid_above_walk_away_maximum"]
    assert client.get(VERDICT).json()["verdicts"] == []


def test_fetching_comparables_makes_an_earlier_verdict_out_of_date(
    client, listing_provider, source_clients, llm_client
):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=well_off_profile())
    llm_client.verdict = bid()
    client.post(VERDICT)

    source_clients["comparables"].facts = SEVERAL
    client.post(FETCH_COMPARABLES)

    state = client.get(VERDICT).json()
    assert state["out_of_date"] is True
    assert state["changed"] == ["case"]


# Price per m² 3000 each: the live Listing asks 595_000 / 152 m² = 3914 per m², 30.5% above.
CHEAPER = [
    comparable("201", 300_000, 100),
    comparable("202", 360_000, 120),
    comparable("203", 450_000, 150),
    comparable("204", 330_000, 110),
    comparable("205", 390_000, 130),
]


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


def houses(category_word, prices_per_m2, first_id=301):
    """Comparables of 100 m² each at these prices per m², all of one soort woning."""
    return [
        comparable(str(first_id + i), per_m2 * 100, 100, object_type="house", house_type=f"Eengezinswoning, {category_word}")
        for i, per_m2 in enumerate(prices_per_m2)
    ]


def test_an_apartment_is_no_comparable_for_a_house(client, listing_provider, source_clients):
    """Five houses at 4000/m² and one apartment at 9000/m²: the apartment does not count."""
    facts = houses("geschakelde woning", [4000] * 5) + [
        comparable("401", 900_000, 100, object_type="apartment", house_type="Bovenwoning")
    ]

    case = with_comparables(
        client, listing_provider, source_clients, facts, object_type="house", house_type="Villa, vrijstaande woning"
    ).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert (metric["count"], metric["excluded"], metric["matched_on"]) == (5, 1, "object_type")
    assert metric["median_price_per_m2"] == 4000


def test_enough_comparables_of_the_same_soort_woning_are_compared_on_their_own(
    client, listing_provider, source_clients
):
    """Five tussenwoningen at 3500/m² and two vrijstaande at 6000/m²: a tussenwoning is compared
    with the five."""
    facts = houses("tussenwoning", [3500] * 5) + houses("vrijstaande woning", [6000, 6000], first_id=351)

    case = with_comparables(
        client, listing_provider, source_clients, facts, object_type="house", house_type="Eengezinswoning, tussenwoning"
    ).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert (metric["count"], metric["excluded"], metric["matched_on"]) == (5, 2, "house_type")
    assert metric["median_price_per_m2"] == 3500


def test_too_few_of_the_same_soort_woning_fall_back_to_all_houses(client, listing_provider, source_clients):
    facts = houses("tussenwoning", [3500] * 4) + houses("vrijstaande woning", [6000], first_id=351)

    case = with_comparables(
        client, listing_provider, source_clients, facts, object_type="house", house_type="Eengezinswoning, tussenwoning"
    ).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert (metric["count"], metric["excluded"], metric["matched_on"]) == (5, 0, "object_type")
    assert metric["coverage"] == "sufficient"


def test_four_comparables_are_thin(client, listing_provider, source_clients):
    case = with_comparables(client, listing_provider, source_clients, SEVERAL[:4]).json()

    assert case["metrics"]["asking_vs_comparables"]["coverage"] == "thin"


def test_comparables_of_unknown_type_get_the_benefit_of_the_doubt(client, listing_provider, source_clients):
    """funda did not say what the five are; only the one known apartment is left out for a house."""
    facts = [comparable(str(500 + i), 400_000, 100) for i in range(5)] + [
        comparable("401", 900_000, 100, object_type="apartment", house_type="Bovenwoning")
    ]

    case = with_comparables(
        client, listing_provider, source_clients, facts, object_type="house", house_type="Villa, vrijstaande woning"
    ).json()

    metric = case["metrics"]["asking_vs_comparables"]
    assert (metric["count"], metric["excluded"], metric["coverage"]) == (5, 1, "sufficient")
