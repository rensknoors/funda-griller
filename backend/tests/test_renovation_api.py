"""Renovation Estimate (Verbouwingsraming) through the HTTP API: items from the cost table, triggered
by Case facts, split by urgency, and subtracted from the affordable and Walk-away maxima."""

import pytest

from app.ports import SourceFact

from app.settings import Settings
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import make_pdf
from tests.profile_fixtures import typical_profile

CASE = "/api/listings/80907644/case"

# A test-owned cost table, so the figures below do not move when the user edits the shipped one.
COST_TABLE = """
version = 7
size_bands = [80, 150]
assumed_living_area = 115

[[items]]
id = "damp_repair"
label = "Vocht- en schimmelherstel"
urgency = "direct"
basis = "fixed"
low = 2000
high = 6000
source = "Testgids"
price_year = 2025
triggers = [{ kind = "equals", fact = "observation.damp_or_mould", values = [true] }]

[[items]]
id = "leak_repair"
label = "Lekkage herstellen"
urgency = "direct"
basis = "fixed"
low = 1000
high = 3000
source = "Testgids"
price_year = 2025
triggers = [
  { kind = "equals", fact = "finding.leak", values = [true] },
  { kind = "equals", fact = "observation.damp_or_mould", values = [true] },
]

[[items]]
id = "roof"
label = "Dak vernieuwen"
urgency = "within_5_years"
basis = "size_band"
low = [8000, 12000, 18000]
high = [14000, 22000, 32000]
source = "Testgids"
price_year = 2025
triggers = [
  { kind = "equals", fact = "observation.roof_condition", values = ["fair"] },
  { kind = "equals", fact = "observation.roof_condition", values = ["poor"], urgency = "direct" },
]

[[items]]
id = "full_renovation"
label = "Volledige renovatie"
urgency = "direct"
basis = "per_m2"
low = 500
high = 1000
source = "Testgids"
price_year = 2025
supersedes = ["kitchen", "cosmetic"]
triggers = [{ kind = "equals", fact = "observation.renovation_needed", values = ["full"] }]

[[items]]
id = "kitchen"
label = "Nieuwe keuken"
urgency = "within_5_years"
basis = "fixed"
low = 8000
high = 20000
source = "Testgids"
price_year = 2024
triggers = [{ kind = "above", fact = "observation.kitchen_age_years", threshold = 20 }]

[[items]]
id = "cosmetic"
label = "Cosmetisch opknappen"
urgency = "optional"
basis = "per_m2"
low = 30
high = 80
source = "Testgids"
price_year = 2025
triggers = [{ kind = "equals", fact = "observation.renovation_needed", values = ["cosmetic"] }]

[[items]]
id = "insulation"
label = "Isoleren"
urgency = "within_5_years"
basis = "per_m2"
low = 50
high = 100
source = "Testgids"
price_year = 2025
triggers = [{ kind = "label_worse_than", fact = ["energielabel.energy_label", "energy_label"], threshold = "D" }]

[[items]]
id = "asbestos_survey"
label = "Asbestinventarisatie"
urgency = "within_5_years"
basis = "fixed"
low = 500
high = 1500
inspection = true
source = "Testgids"
price_year = 2025
triggers = [{ kind = "below", fact = "construction_year", threshold = 1994 }]

[[items]]
id = "insulation_check"
label = "Energieadvies"
urgency = "within_5_years"
basis = "fixed"
low = 300
high = 700
inspection = true
source = "Testgids"
price_year = 2025
triggers = [
  { kind = "below", fact = "construction_year", threshold = 1975, also = [
    { kind = "absent", fact = ["energielabel.energy_label", "energy_label"] },
  ] },
]
"""

PHOTO_DAMP = {"key": "damp_or_mould", "value": True, "photos": [1], "note": "Vochtplek boven het raam"}
LEAK = {
    "topic": "leak",
    "present": True,
    "statement": "Lekkage in de badkamer in 2024.",
    "quote": "Ja, in de badkamer in 2024.",
    "page": 2,
}
VRAGENLIJST = make_pdf(["Vragenlijst", "Zijn er lekkages geweest? Ja, in de badkamer in 2024."])


@pytest.fixture
def settings(tmp_path):
    cost_table = tmp_path / "renovation_costs.toml"
    cost_table.write_text(COST_TABLE)
    return Settings(
        _env_file=None,
        database_path=tmp_path / "test.sqlite",
        media_dir=tmp_path / "media",
        renovation_costs_path=cost_table,
    )


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**{"brochure_url": None, **overrides})
    assert client.post("/api/listings", json={"url": LIVE_URL}).status_code == 201


def estimate(client):
    return client.get(CASE).json()["renovation_estimate"]


def items(client):
    return {item["id"]: item for item in estimate(client)["items"]}


def test_an_observation_triggers_an_estimated_item_citing_its_photos(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)

    damp = items(client)["damp_repair"]

    assert damp["label"] == "Vocht- en schimmelherstel"
    assert damp["urgency"] == "direct"
    assert (damp["low"], damp["high"]) == (2000, 6000)
    assert damp["estimated"] is True
    assert (damp["source"], damp["price_year"]) == ("Testgids", 2025)
    [evidence] = damp["evidence"]
    assert evidence["key"] == "damp_or_mould"
    assert evidence["provenance"] == "observation"
    assert [photo["number"] for photo in evidence["photos"]] == [1]


def upload_vragenlijst(client, llm_client, *findings):
    llm_client.findings = list(findings)
    response = client.post(
        "/api/listings/80907644/documents", files={"file": ("Vragenlijst.pdf", VRAGENLIJST, "application/pdf")}
    )
    assert response.status_code == 201, response.text


def test_an_item_triggered_by_several_facts_is_listed_once_citing_them_all(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)
    upload_vragenlijst(client, llm_client, LEAK)

    leak = [item for item in estimate(client)["items"] if item["id"] == "leak_repair"]

    assert len(leak) == 1
    assert {(fact["key"], fact["provenance"]) for fact in leak[0]["evidence"]} == {
        ("leak", "finding"),
        ("damp_or_mould", "observation"),
    }
    finding = next(fact for fact in leak[0]["evidence"] if fact["provenance"] == "finding")
    assert (finding["document_name"], finding["page"]) == ("Vragenlijst.pdf", 2)


def test_an_item_takes_the_most_urgent_class_of_its_triggers(client, listing_provider, llm_client):
    llm_client.observations = [{"key": "roof_condition", "value": "poor", "photos": [1], "note": "Mos en gaten"}]
    capture(client, listing_provider)

    assert items(client)["roof"]["urgency"] == "direct"


def test_a_full_renovation_supersedes_the_kitchen_and_cosmetic_items(client, listing_provider, llm_client):
    llm_client.observations = [
        {"key": "renovation_needed", "value": "full", "photos": [1], "note": "Casco"},
        {"key": "kitchen_age_years", "value": 30, "photos": [2], "note": "Oude keuken"},
    ]
    capture(client, listing_provider)

    found = items(client)

    assert "full_renovation" in found
    assert "kitchen" not in found


@pytest.mark.parametrize(
    ("living_area", "roof", "full_renovation", "assumed"),
    [
        (70, (8000, 14000), (35_000, 70_000), False),
        (152, (18000, 32000), (76_000, 152_000), False),
        (None, (12000, 22000), (57_500, 115_000), True),
    ],
)
def test_size_based_items_follow_the_living_area_and_say_when_it_is_assumed(
    client, listing_provider, llm_client, living_area, roof, full_renovation, assumed
):
    llm_client.observations = [
        {"key": "roof_condition", "value": "fair", "photos": [1], "note": "Dakpannen verkleurd"},
        {"key": "renovation_needed", "value": "full", "photos": [2], "note": "Casco"},
    ]
    capture(client, listing_provider, living_area=living_area)

    found = items(client)

    assert (found["roof"]["low"], found["roof"]["high"]) == roof
    assert (found["full_renovation"]["low"], found["full_renovation"]["high"]) == full_renovation
    assert found["roof"]["size_assumed"] is assumed
    assert found["full_renovation"]["size_assumed"] is assumed


def test_a_poor_energielabel_triggers_insulation(client, listing_provider):
    capture(client, listing_provider, energy_label="F", living_area=100)

    insulation = items(client)["insulation"]

    assert (insulation["urgency"], insulation["low"], insulation["high"]) == ("within_5_years", 5000, 10000)
    assert {fact["key"] for fact in insulation["evidence"]} == {"energy_label", "living_area"}


def test_the_build_year_triggers_inspections_not_repairs(client, listing_provider):
    capture(client, listing_provider, construction_year=1962, energy_label=None)

    found = items(client)

    assert found["asbestos_survey"]["inspection"] is True
    assert [fact["key"] for fact in found["asbestos_survey"]["evidence"]] == ["construction_year"]
    assert found["insulation_check"]["inspection"] is True
    assert "damp_repair" not in found


def test_a_known_energielabel_needs_no_insulation_check(client, listing_provider):
    capture(client, listing_provider, construction_year=1962, energy_label="B")

    assert "insulation_check" not in items(client)


def test_without_photos_documents_or_energielabel_nothing_is_guessed_and_the_gaps_are_listed(
    client, listing_provider
):
    capture(client, listing_provider, photo_urls=(), energy_label=None, construction_year=2005)

    result = estimate(client)

    assert result["items"] == []
    assert result["missing_inputs"] == ["observations", "vragenlijst", "energielabel"]
    assert result["classes"]["direct"] == {"low": 0, "high": 0, "midpoint": 0}


def test_an_uploaded_vragenlijst_and_photos_are_no_longer_missing(client, listing_provider, llm_client):
    capture(client, listing_provider)
    upload_vragenlijst(client, llm_client)

    assert estimate(client)["missing_inputs"] == []


def test_the_estimate_records_the_cost_table_version_and_class_totals(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)

    case = client.get(CASE).json()

    assert case["built_from"]["cost_table_version"] == 7
    assert case["renovation_estimate"]["cost_table_version"] == 7
    # damp_repair 2000-6000 plus leak_repair 1000-3000, both Direct nodig.
    assert case["renovation_estimate"]["classes"]["direct"] == {"low": 3000, "high": 9000, "midpoint": 6000}
    # The 1931 build year asks for an asbestos survey.
    assert case["renovation_estimate"]["classes"]["within_5_years"] == {"low": 500, "high": 1500, "midpoint": 1000}


def test_the_estimate_is_the_same_for_every_buyer_profile(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)
    without_profile = estimate(client)

    client.put("/api/buyer-profile", json=typical_profile() | {"renovation_tolerance": 1})
    cautious = estimate(client)
    client.put("/api/buyer-profile", json=typical_profile() | {"renovation_tolerance": 5})
    bold = estimate(client)

    def figures(result):
        return [(i["id"], i["urgency"], i["low"], i["high"]) for i in result["items"]], result["classes"]

    assert figures(without_profile) == figures(cautious) == figures(bold)


VERDICT = "/api/listings/80907644/verdict"
# The typical household can pay at most 704_519 for the live Listing when nothing is Direct nodig.
AFFORDABLE_MAXIMUM = 704_519
# Its available funds, less the 6000 Direct nodig midpoint of damp_repair and leak_repair, over 1.02.
AFFORDABLE_MAXIMUM_AFTER_DAMP = 698_637


def bid():
    return {
        "tier": "consider",
        "summary": "Prima woning.",
        "reasoning": "Past bij de wensen.",
        "cited_flags": [],
        "bid_advice": {"opening_bid": 560_000, "conditions": ["Bouwkundige keuring"]},
    }


def test_direct_nodig_lowers_the_affordable_maximum(client, listing_provider, llm_client):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    assert client.get(CASE).json()["affordability"]["affordable_maximum"] == AFFORDABLE_MAXIMUM

    llm_client.observations = [PHOTO_DAMP]
    assert client.post("/api/listings/80907644/observations").status_code == 200
    affordability = client.get(CASE).json()["affordability"]

    assert affordability["renovation_direct"] == 6000
    assert affordability["affordable_maximum"] == AFFORDABLE_MAXIMUM_AFTER_DAMP
    assert affordability["headroom"] == AFFORDABLE_MAXIMUM_AFTER_DAMP - 595_000


def test_direct_nodig_comes_off_the_asking_price_basis_of_the_walk_away_maximum(
    client, listing_provider, llm_client
):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    # (595_000 - 6_000) x 1.05
    assert advice["walk_away_maximum"] == 618_450
    assert advice["affordable_maximum"] == AFFORDABLE_MAXIMUM_AFTER_DAMP
    assert advice["derivation"]["renovation_direct"] == 6000
    assert advice["derivation"]["basis"] == "asking_price"


def test_direct_nodig_comes_off_the_comparables_basis_of_the_walk_away_maximum(
    client, listing_provider, llm_client, source_clients
):
    # Price per m² 4000, 4000, 4200 -> median 4000, so 152 m² is worth 608_000 by comparables.
    source_clients["comparables"].facts = [
        SourceFact("comparable", {"funda_id": n, "asking_price": price, "living_area": area})
        for n, price, area in (("101", 500_000, 125), ("102", 480_000, 120), ("103", 630_000, 150))
    ]
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)
    client.post("/api/listings/80907644/sources/comparables/refetch")
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    # (608_000 - 6_000) x 1.10
    assert advice["walk_away_maximum"] == 662_200
    assert advice["derivation"]["basis"] == "comparables"
    assert advice["derivation"]["renovation_direct"] == 6000


def test_without_direct_nodig_items_the_maxima_are_unchanged(client, listing_provider, llm_client):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid()

    advice = client.post(VERDICT).json()["bid_advice"]

    assert advice["walk_away_maximum"] == 624_750
    assert advice["affordable_maximum"] == AFFORDABLE_MAXIMUM
    assert advice["derivation"]["renovation_direct"] == 0


# Roof poor on 152 m² (18_000-32_000), damp (2_000-6_000) and the leak it implies (1_000-3_000):
# Direct nodig 21_000-41_000, midpoint 31_000, above the 25_000 threshold.
HIGH_DIRECT = [PHOTO_DAMP, {"key": "roof_condition", "value": "poor", "photos": [1], "note": "Gaten in het dak"}]


def test_a_high_direct_nodig_total_raises_a_con_flag_citing_it(client, listing_provider, llm_client):
    llm_client.observations = HIGH_DIRECT
    capture(client, listing_provider)

    flag = next(f for f in client.get(CASE).json()["flags"] if f["rule_id"] == "renovation_direct_high")

    assert flag["class"] == "con"
    assert [(e["key"], e["value"]) for e in flag["evidence"]] == [
        ("renovation_direct_midpoint", 31_000),
        ("threshold", 25_000),
    ]


def test_a_low_direct_nodig_total_raises_no_flag(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)

    assert "renovation_direct_high" not in {f["rule_id"] for f in client.get(CASE).json()["flags"]}


def test_an_opknapper_deal_breaker_is_a_hard_no_that_skips_the_llm_and_keeps_the_estimate(
    client, listing_provider, llm_client
):
    llm_client.observations = HIGH_DIRECT
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile() | {"deal_breakers": ["Geen opknapper"]})

    case = client.get(CASE).json()
    verdict = client.post(VERDICT).json()

    assert case["hard_no"]["flag_id"] == "renovation_direct_high"
    assert case["renovation_estimate"]["classes"]["direct"]["midpoint"] == 31_000
    assert verdict["tier"] == "hard_no"
    assert llm_client.rate_calls == []


def test_the_model_receives_the_estimate_with_its_evidence(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid()

    client.post(VERDICT)

    [(sent, _)] = llm_client.rate_calls
    sent_items = {item["id"]: item for item in sent["renovation_estimate"]["items"]}
    assert sent_items["damp_repair"]["evidence"][0]["provenance"] == "observation"
    assert sent["renovation_estimate"]["classes"]["direct"]["midpoint"] == 6000


def test_a_cost_table_change_marks_the_verdict_achterhaald(client, listing_provider, llm_client, settings):
    capture(client, listing_provider)
    client.put("/api/buyer-profile", json=typical_profile())
    llm_client.verdict = bid()
    client.post(VERDICT)
    assert client.get(VERDICT).json()["changed"] == []

    settings.renovation_costs_path.write_text(COST_TABLE.replace("version = 7", "version = 8", 1))

    assert client.get(VERDICT).json()["changed"] == ["rules"]


def test_the_comparison_row_shows_direct_nodig(client, listing_provider, llm_client):
    llm_client.observations = [PHOTO_DAMP]
    capture(client, listing_provider)

    [row] = client.get("/api/listings").json()

    assert row["comparison"]["renovation_direct"] == {"low": 3000, "high": 9000, "midpoint": 6000}


@pytest.mark.parametrize(("topic", "item"), [("boiler_old", "boiler"), ("wiring_old", "wiring")])
def test_an_old_boiler_or_wiring_from_the_vragenlijst_is_priced_by_the_shipped_table(
    client, listing_provider, llm_client, settings, topic, item
):
    settings.renovation_costs_path = Settings(_env_file=None).renovation_costs_path
    capture(client, listing_provider)
    upload_vragenlijst(client, llm_client, {**LEAK, "topic": topic})

    assert items(client)[item]["urgency"] == "within_5_years"
