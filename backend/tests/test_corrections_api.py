"""Corrections (Correcties) through the HTTP API: the household's own value for a Listing fact the
Case computes with, applied before the Case derives anything, with the original kept beside it."""

import pytest

from app.ports import SourceFact

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import well_off_profile
from tests.test_comparables_api import FETCH_COMPARABLES, comparable

CASE = "/api/listings/80907644/case"
VERDICT = "/api/listings/80907644/verdict"
CORRECTIONS = "/api/listings/80907644/corrections"
NEN = "NEN 2580-meetrapport"
# Price per m² 3000..5000 with a median of 4000 and an interquartile range of 3500 to 4500.
SPREAD = [comparable(str(i), price * 10_000, 100) for i, price in zip(range(101, 106), (30, 35, 40, 45, 50))]


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    assert client.post("/api/listings", json={"url": LIVE_URL}).status_code == 201


def with_comparables(client, listing_provider, source_clients, facts=SPREAD, **overrides):
    capture(client, listing_provider, **overrides)
    source_clients["comparables"].facts = facts
    client.post(FETCH_COMPARABLES)


def correct(client, key, value, explanation=NEN):
    return client.put(f"{CORRECTIONS}/{key}", json={"value": value, "explanation": explanation})


def fact(case, key):
    return next(f for f in case["facts"] if f["key"] == key and f["provenance"] in ("listing", "correction"))


def test_a_correction_replaces_the_listing_fact_and_keeps_the_original_beside_it(client, listing_provider):
    capture(client, listing_provider)

    response = correct(client, "living_area", 112)

    assert response.status_code == 200
    corrected = fact(client.get(CASE).json(), "living_area")
    assert corrected["value"] == 112
    assert corrected["provenance"] == "correction"
    assert corrected["original"] == {"value": 152, "provenance": "listing"}
    assert corrected["explanation"] == NEN
    assert corrected["listing_changed"] is False
    assert fact(response.json(), "living_area")["value"] == 112


def test_a_corrected_living_area_moves_every_figure_derived_from_it(client, listing_provider, source_clients):
    with_comparables(client, listing_provider, source_clients)

    metrics = correct(client, "living_area", 112).json()["metrics"]

    vs_comparables = metrics["asking_vs_comparables"]
    assert vs_comparables["price_per_m2"] == 5312  # 595.000 / 112
    assert vs_comparables["percent"] == 32.8
    assert vs_comparables["comparables_value"] == 448_000  # 4000 * 112
    expected = metrics["expected_sale_price"]
    # 448.000 plus the average overbid of 4,6%; the range from 3500 and 4500 per m².
    assert (expected["value"], expected["low"], expected["high"]) == (468_608, 410_032, 527_184)
    assert metrics["asking_vs_expected"]["prijsstelling"] == "hoog ingezet"


def test_a_corrected_living_area_resizes_the_renovation_estimate(client, listing_provider):
    capture(client, listing_provider, energy_label="F")

    case = correct(client, "living_area", 112).json()

    insulation = next(i for i in case["renovation_estimate"]["items"] if i["id"] == "insulation")
    # The shipped cost table prices insulation at 60 to 140 per m².
    assert (insulation["low"], insulation["high"]) == (6_720, 15_680)
    assert fact(case, "living_area") in insulation["evidence"]


def test_a_corrected_living_area_moves_the_walk_away_maximum_and_the_guide_bid(
    client, listing_provider, source_clients, llm_client
):
    with_comparables(client, listing_provider, source_clients)
    client.put("/api/buyer-profile", json=well_off_profile())
    correct(client, "living_area", 112)
    llm_client.verdict = {
        "tier": "consider",
        "summary": "Kleiner dan gesteld.",
        "reasoning": "De woonoppervlakte is kleiner dan de makelaar opgaf.",
        "cited_flags": [],
        "bid_advice": {"opening_bid": 440_000, "deviation_reason": None, "conditions": ["Financieringsvoorbehoud"]},
    }

    response = client.post(VERDICT)

    assert response.status_code == 201
    advice = response.json()["bid_advice"]
    assert advice["expected_sale_price"] == 468_608
    assert advice["walk_away_maximum"] == 492_038  # 468.608 * 1,05
    # Hoog ingezet: 6% off 468.608, rounded down to 500.
    assert advice["guide_bid"]["value"] == 440_000


def test_a_corrected_house_type_changes_which_comparables_count(client, listing_provider, source_clients):
    tussen = [comparable(str(i), 400_000, 100, house_type="Eengezinswoning, tussenwoning") for i in range(201, 206)]
    vrijstaand = [comparable(str(i), 800_000, 100, house_type="Vrijstaande woning") for i in range(301, 306)]
    with_comparables(client, listing_provider, source_clients, tussen + vrijstaand)

    metric = correct(client, "house_type", "Eengezinswoning, tussenwoning").json()["metrics"]["asking_vs_comparables"]

    assert metric["matched_on"] == "house_type"
    assert metric["count"] == 5
    assert metric["median_price_per_m2"] == 4000


def test_a_corrected_energielabel_outranks_the_register(client, listing_provider, source_clients):
    source_clients["energielabel"].facts = [SourceFact(name="energy_label", value="G", as_of="2020-01-01")]
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=well_off_profile())

    case = correct(client, "energy_label", "a", "Nieuw label na isolatie, afgemeld bij EP-Online").json()

    assert fact(case, "energy_label")["value"] == "A"
    assert fact(case, "energy_label")["original"] == {"value": "G", "provenance": "source"}
    assert case["affordability"]["energy_label"] == "A"
    flags = {flag["id"] for flag in case["flags"]}
    assert "energy_label_efficient" in flags
    assert "energy_label_below_tolerance" not in flags


def test_a_correction_fills_a_fact_the_listing_leaves_out(client, listing_provider, source_clients):
    with_comparables(client, listing_provider, source_clients, living_area=None)

    case = correct(client, "living_area", 112).json()

    assert fact(case, "living_area")["original"] == {"value": None, "provenance": None}
    assert case["metrics"]["expected_sale_price"]["value"] == 468_608


def test_removing_a_correction_restores_the_listing_fact(client, listing_provider):
    capture(client, listing_provider)
    correct(client, "living_area", 112)

    response = client.delete(f"{CORRECTIONS}/living_area")

    assert response.status_code == 200
    restored = fact(client.get(CASE).json(), "living_area")
    assert (restored["value"], restored["provenance"]) == (152, "listing")
    assert client.delete(f"{CORRECTIONS}/living_area").status_code == 404


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("living_area", 0),
        ("living_area", -5),
        ("living_area", 112.5),
        ("living_area", "112"),
        ("plot_area", True),
        ("rooms", 0),
        ("bedrooms", None),
        ("construction_year", 999),
        ("construction_year", 2200),
        ("energy_label", "H"),
        ("house_type", "Kasteel"),
        ("ownership_situation", "  "),
    ],
)
def test_an_implausible_value_is_rejected(client, listing_provider, key, value):
    capture(client, listing_provider)

    response = correct(client, key, value)

    assert response.status_code == 422
    assert response.json() == {"code": "invalid_value"}


def test_only_the_listing_facts_the_case_computes_with_can_be_corrected(client, listing_provider):
    capture(client, listing_provider)

    for key in ("asking_price", "address", "heating", "woz_value"):
        response = correct(client, key, 1)
        assert response.status_code == 422
        assert response.json() == {"code": "not_correctable"}


@pytest.mark.parametrize("explanation", ["", "   "])
def test_a_correction_needs_an_explanation(client, listing_provider, explanation):
    capture(client, listing_provider)

    response = correct(client, "living_area", 112, explanation)

    assert response.status_code == 422
    assert response.json() == {"code": "explanation_required"}
    assert fact(client.get(CASE).json(), "living_area")["provenance"] == "listing"


def test_an_unknown_listing_cannot_be_corrected(client):
    assert correct(client, "living_area", 112).status_code == 404


def test_a_recapture_keeps_the_correction_and_says_when_the_listing_has_moved(client, listing_provider):
    capture(client, listing_provider)
    correct(client, "living_area", 112)

    client.post("/api/listings/80907644/refetch")
    unchanged = fact(client.get(CASE).json(), "living_area")
    listing_provider.listings[LIVE_URL] = live_listing(living_area=130)
    client.post("/api/listings/80907644/refetch")
    moved = fact(client.get(CASE).json(), "living_area")

    assert (unchanged["value"], unchanged["listing_changed"]) == (112, False)
    assert (moved["value"], moved["listing_changed"]) == (112, True)
    assert moved["original"] == {"value": 130, "provenance": "listing"}


def test_the_model_sees_the_corrected_value_the_original_and_the_explanation(client, listing_provider, llm_client):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=well_off_profile())
    correct(client, "living_area", 112)

    client.post(VERDICT)

    [(sent_case, _)] = llm_client.rate_calls
    sent = next(f for f in sent_case["facts"] if f["key"] == "living_area")
    assert sent["value"] == 112
    assert sent["original"] == {"value": 152, "provenance": "listing"}
    assert sent["explanation"] == NEN
    assert "correction" in sent_case["provenance_legend"]


def test_a_correction_change_makes_the_verdict_achterhaald(client, listing_provider):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=well_off_profile())
    client.post(VERDICT)

    correct(client, "living_area", 112)
    after_correcting = client.get(VERDICT).json()
    client.post(VERDICT)
    correct(client, "living_area", 110)
    after_changing = client.get(VERDICT).json()
    client.post(VERDICT)
    client.delete(f"{CORRECTIONS}/living_area")
    after_removing = client.get(VERDICT).json()

    for state in (after_correcting, after_changing, after_removing):
        assert state["out_of_date"] is True
        assert state["changed"] == ["case"]
