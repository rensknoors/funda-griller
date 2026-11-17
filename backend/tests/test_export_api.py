"""Markdown export (Exporteer als Markdown), through the HTTP API: one Dutch `.md` file holding a
house's Case and current Verdict, for pasting into another LLM chat. The Buyer Profile part is
always anonymised and can be left out."""

import re

import pytest

from app import store
from app.gemini_client import VERDICT_PROMPT_VERSION
from app.ports import PricePoint, SourceFact
from tests.fakes import FakeGeocoder, FakeTravelTimeRouter
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile
from tests.test_comparables_api import FETCH_COMPARABLES, SEVERAL

pytestmark = pytest.mark.usefixtures("price_at_asking")

EXPORT = "/api/listings/80907644/export.md"
VERDICT = "/api/listings/80907644/verdict"


def capture(client, listing_provider, profile=None, **listing_overrides):
    if profile is not False:
        client.put("/api/buyer-profile", json=profile or typical_profile())
    listing_provider.listings[LIVE_URL] = live_listing(**listing_overrides)
    client.post("/api/listings", json={"url": LIVE_URL})


def test_the_export_is_a_markdown_download_named_after_date_and_address(client, listing_provider):
    capture(client, listing_provider)

    response = client.get(EXPORT)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == 'attachment; filename="2026-10-24-buchterweg-15-holtum.md"'


def test_an_unknown_listing_has_no_export(client):
    assert client.get("/api/listings/404/export.md").status_code == 404


def model_says(tier="consider", opening_bid=585_000):
    return {
        "tier": tier,
        "summary": "Degelijke woning, prijs aan de hoge kant.",
        "reasoning": "De woning past bij jullie wensen; de vraagprijs ligt ruim boven de WOZ.",
        "cited_flags": [],
        "bid_advice": {"opening_bid": opening_bid, "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"]},
    }


def headings(markdown):
    return [line for line in markdown.splitlines() if line.startswith("## ")]


def test_a_full_case_with_a_verdict_exports_every_section_in_order(client, listing_provider, llm_client):
    capture(client, listing_provider, description="Vrijstaande woning met garage.\n\nRuime tuin op het zuiden.")
    llm_client.verdict = model_says()
    client.post(VERDICT)

    markdown = client.get(EXPORT).text

    assert headings(markdown) == [
        "## Over dit bestand",
        "## Herkomst van dit dossier",
        "## Woning",
        "## Feiten",
        "## Kengetallen",
        "## Vergelijkbare woningen",
        "## Signalen",
        "## Verbouwingsraming",
        "## Oordeel",
        "## Biedadvies",
        "## Koperprofiel (geanonimiseerd)",
    ]
    assert "Funda Griller" in markdown
    assert "Dossier = Case" in markdown and "Oordeel = Verdict" in markdown and "Biedadvies = Bid Advice" in markdown
    assert "Buchterweg 15, Holtum" in markdown
    assert "€ 595.000" in markdown
    assert LIVE_URL in markdown
    assert "Vrijstaande woning met garage.\n\nRuime tuin op het zuiden." in markdown
    assert "Overwegen" in markdown
    assert "De woning past bij jullie wensen" in markdown
    assert "Openingsbod: € 585.000" in markdown
    assert "Maximumbod: € 624.750" in markdown
    assert "- Bouwkundige keuring" in markdown
    assert "2026-10-24T12:00:00+00:00" in markdown
    assert f"Promptversie Oordeel: {VERDICT_PROMPT_VERSION}" in markdown
    assert "Koperprofiel meegestuurd: ja (geanonimiseerd)" in markdown


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


def test_facts_are_grouped_by_provenance_with_their_trust_markers(
    client, listing_provider, source_clients, llm_client, settings, clock
):
    settings.source_ttl_days = {"woz": 30}
    source_clients["woz"].facts = [SourceFact("woz_value", 392_000, "2025-01-01")]
    source_clients["comparables"].facts = [comparable("101", 500_000, 125), comparable("104", 360_000, 100, False)]
    llm_client.observations = [{"key": "kitchen_age_years", "value": 25, "photos": [1], "note": "Oude keuken."}]
    llm_client.findings = [
        {"topic": "erfpacht", "present": True, "statement": "Erfpacht afgekocht tot 2050.", "quote": "Ligging en indeling", "page": 2}
    ]
    capture(client, listing_provider)
    client.post("/api/listings/80907644/sources/comparables/refetch")
    clock.advance(days=31)

    markdown = client.get(EXPORT).text

    facts = markdown.split("## Feiten")[1].split("## Kengetallen")[0]
    assert "### Advertentie\n\n- Adres: Buchterweg 15" in facts
    assert "WOZ-waarde: € 392.000 (Bron: woz, derde partij, indicatief, peildatum 2025-01-01" in facts
    assert "**Verouderd**" in facts
    assert "Keuken, geschatte leeftijd (jaar): ≈ 25 (geschat, foto 1) — Oude keuken." in facts
    assert "Erfpacht (van toepassing): Erfpacht afgekocht tot 2050. (door verkoper, p. 2)" in facts
    # Documents are shown only in the app's own UI: no verbatim quote, no document name.
    assert "Ligging en indeling" not in markdown and "Brochure" not in markdown
    assert "Vraagprijs t.o.v. WOZ: +51,8%" in markdown
    listed = markdown.split("## Vergelijkbare woningen")[1].split("## Signalen")[0]
    assert "- Dorpsstraat 101, Holtum: € 500.000, 125 m², € 4.000 per m², verkocht" in listed
    assert "- Dorpsstraat 104, Holtum: € 360.000, 100 m², € 3.600 per m², te koop" in listed


OFFICE = "Kantoorlaan 1, Eindhoven"
OFFICE_AT = (51.44, 5.47)
HOME_ADDRESS = "Eikenlaan 12, Utrecht"


@pytest.fixture
def geocoder():
    found = FakeGeocoder()
    found.places = {OFFICE: OFFICE_AT}
    return found


@pytest.fixture
def router():
    found = FakeTravelTimeRouter()
    found.minutes = {("car", OFFICE_AT): 52.0, ("bike", OFFICE_AT): 140.0}
    return found


def private_profile():
    """Distinctive figures, so any leak of them is unmistakable."""
    return {
        "household": [
            {"role": "adult", "birth_date": "1988-04-12"},
            {"role": "adult", "birth_date": "1990-09-30"},
            {"role": "child", "birth_date": "2020-01-15"},
        ],
        "gross_annual_income": 87_321,
        "assets": {"savings": 41_234, "investments": 15_678},
        "current_home": {
            "value": 412_345,
            "outstanding_mortgage": 221_111,
            "selling_costs": 8_765,
            "address": HOME_ADDRESS,
        },
        "must_haves": ["Tuin op het zuiden"],
        "nice_to_haves": ["Garage"],
        "deal_breakers": ["Geen flat"],
        "commute_destinations": [{"label": "Kantoor Philips", "address": OFFICE, "max_minutes": 30}],
        "renovation_tolerance": 3,
    }


def mentions(markdown, amount):
    """Whether an amount appears in any common notation, not as part of a longer number."""
    forms = {str(amount), f"{amount:,}", f"{amount:,}".replace(",", ".")}
    return any(re.search(rf"(?<![\d.,]){re.escape(form)}(?![\d]|[.,]\d)", markdown) for form in forms)


def test_the_buyer_profile_part_is_anonymised(client, listing_provider, llm_client):
    capture(client, listing_provider, private_profile())
    llm_client.verdict = model_says() | {"reasoning": "Te ver van Kantoor Philips met de fiets."}
    client.post(VERDICT)
    affordability =client.get("/api/listings/80907644/case").json()["affordability"]

    markdown = client.get(EXPORT).text

    for raw in (87_321, 41_234, 15_678, 412_345, 221_111, 8_765):
        assert not mentions(markdown, raw), raw
    exact_home_equity = 412_345 - 221_111 - 8_765
    for exact in (
        exact_home_equity,
        affordability["affordable_maximum"],
        affordability["headroom"],
        affordability["monthly_cost"],
        affordability["monthly_cost_net"],
    ):
        assert not mentions(markdown, exact), exact
    for private in (HOME_ADDRESS, "Eikenlaan", OFFICE, "Kantoorlaan", "Kantoor Philips"):
        assert private not in markdown
    assert "Overwaarde huidige woning: ≈ € 180.000" in markdown
    assert "2 volwassene(n), 1 kind(eren)" in markdown
    assert "Bestemming 1: maximaal 30 min" in markdown
    assert "Reistijd naar Bestemming 1: 52 min met de auto" in markdown
    assert "Reistijd boven je maximum: Bestemming 1" in markdown
    assert "Te ver van Bestemming 1 met de fiets." in markdown
    for preference in ("Tuin op het zuiden", "Garage", "Geen flat"):
        assert f"  - {preference}" in markdown
    # The bids stay exact; the Walk-away Maximum here rests on the asking price, not affordability.
    assert "Openingsbod: € 585.000" in markdown
    assert "Maximumbod: € 624.750" in markdown
    assert "begrensd door de basis" in markdown


def top(markdown):
    return markdown.split("## Over dit bestand")[0]


def test_without_a_verdict_the_export_says_so_at_the_top(client, listing_provider):
    capture(client, listing_provider)

    markdown = client.get(EXPORT).text

    assert "nog geen Oordeel" in top(markdown)
    assert "Nog geen Oordeel." in markdown.split("## Oordeel")[1]


def test_an_out_of_date_verdict_is_called_achterhaald_at_the_top(client, listing_provider, llm_client):
    capture(client, listing_provider)
    llm_client.verdict = model_says()
    client.post(VERDICT)
    client.put("/api/buyer-profile", json=typical_profile() | {"renovation_tolerance": 5})

    markdown = client.get(EXPORT).text

    assert "**Achterhaald**" in top(markdown)
    assert "het Koperprofiel" in top(markdown)
    assert "Overwegen" in markdown.split("## Oordeel")[1]


def test_a_hard_no_is_said_plainly_at_the_top_and_carries_no_bid_advice(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Geen erfpacht"]}
    capture(client, listing_provider, profile, description="Appartement op erfpacht.")
    client.post(VERDICT)

    markdown = client.get(EXPORT).text

    assert "**Harde afwijzing**" in top(markdown)
    assert "Harde afwijzing" in markdown.split("## Oordeel")[1]
    assert "Model Oordeel: geen (deterministisch)" in markdown
    assert "Geen Biedadvies bij dit Oordeel." in markdown


def test_without_the_profile_no_profile_or_affordability_figures_are_exported(client, listing_provider, llm_client):
    capture(client, listing_provider, private_profile())
    llm_client.verdict = model_says()
    client.post(VERDICT)

    markdown = client.get(f"{EXPORT}?profile=false").text

    assert "Koperprofiel meegestuurd: nee" in markdown
    assert "## Koperprofiel\n\nNiet meegestuurd." in markdown
    assert "Overwaarde" not in markdown
    assert "Betaalbaarheid" not in markdown
    assert "≈ €" not in markdown
    assert "Hoe het Maximumbod is berekend" not in markdown
    # Flags raised from the Buyer Profile (a missing Must-have, a commute over its limit) would
    # carry the profile along, so they are left out and counted.
    for preference in ("Tuin op het zuiden", "Garage", "Geen flat", "Kantoor Philips", "Bestemming 1: maximaal"):
        assert preference not in markdown
    assert "Must-have ontbreekt" not in markdown and "Reistijd boven je maximum" not in markdown
    assert "Signalen uit het Koperprofiel weggelaten: 2" in markdown
    assert "Reistijd naar Bestemming 1: 52 min met de auto" in markdown
    assert "maximum 30 min" not in markdown
    bid = markdown.split("## Biedadvies")[1]
    assert "Openingsbod: € 585.000" in bid and "Maximumbod: € 624.750" in bid and "Financieringsvoorbehoud" in bid


def test_an_affordability_bound_walk_away_maximum_is_said_in_words(client, listing_provider, llm_client):
    poorer = typical_profile() | {"gross_annual_income": 30_000, "assets": {"savings": 5_000, "investments": 0}}
    capture(client, listing_provider, poorer)
    llm_client.verdict = lambda case, _: model_says(opening_bid=case["guide_bid"]["value"] - 1)
    verdict = client.post(VERDICT).json()

    markdown = client.get(EXPORT).text

    assert verdict["bid_advice"]["derivation"]["binding"] == "affordability"
    assert "**begrensd door betaalbaarheid**" in markdown
    assert f"Maximumbod: € {verdict['bid_advice']['walk_away_maximum']:,}".replace(",", ".") in markdown


def test_no_photo_or_document_is_linked(client, listing_provider, llm_client):
    llm_client.findings = [
        {"topic": "erfpacht", "present": True, "statement": "Erfpacht.", "quote": "Ligging en indeling", "page": 2}
    ]
    capture(client, listing_provider)
    listing = client.get("/api/listings").json()[0]
    photo_urls = [p["url"] for p in listing["snapshots"][0]["photos"]]

    markdown = client.get(EXPORT).text

    assert photo_urls
    for url in [*photo_urls, "https://cloud.funda.nl/p1.jpg", "https://cloud.funda.nl/brochure.pdf"]:
        assert url not in markdown
    assert "/photos/" not in markdown and "/documents/" not in markdown
    assert ".jpg" not in markdown and ".pdf" not in markdown


# A test-owned cost table, so the figures below do not move when the shipped one is edited.
COST_TABLE = """
version = 7
size_bands = [80, 150]
assumed_living_area = 115

[[items]]
id = "damp_repair"
label = "Vochtprobleem verhelpen"
urgency = "direct"
basis = "fixed"
low = 2000
high = 6000
source = "Testgids"
price_year = 2025
triggers = [{ kind = "equals", fact = "observation.damp_or_mould", values = [true] }]

[[items]]
id = "roof"
label = "Dak vernieuwen"
urgency = "within_5_years"
basis = "size_band"
low = [8000, 12000, 18000]
high = [14000, 22000, 32000]
source = "Testgids"
price_year = 2024
triggers = [{ kind = "equals", fact = "observation.roof_condition", values = ["fair"] }]

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
"""


def section(markdown, heading):
    return markdown.split(f"## {heading}\n")[1].split("\n## ")[0]


def test_the_export_gives_the_richtbod_with_the_models_reason_and_the_discount_breakdown(
    client, listing_provider, llm_client
):
    capture(client, listing_provider)
    llm_client.verdict = model_says() | {
        "bid_advice": {
            "opening_bid": 590_000,
            "conditions": [],
            "deviation_reason": "Vocht in de kelder.",
        }
    }
    client.post(VERDICT)

    bid = section(client.get(EXPORT).text, "Biedadvies")

    assert "- Openingsbod: € 590.000" in bid
    assert "- Richtbod: € 580.000 (afwijking: Vocht in de kelder.)" in bid
    assert "### Hoe het Richtbod is berekend" in bid
    assert "- Prijsstelling: marktconform, 2,5% korting op de verwachte verkoopprijs" in bid
    assert "**Zwak onderbouwd**" in bid


def test_the_export_leaves_out_the_richtbod_line_when_the_opening_bid_equals_it(
    client, listing_provider, llm_client
):
    capture(client, listing_provider)
    llm_client.verdict = model_says(opening_bid=580_000)
    client.post(VERDICT)

    bid = section(client.get(EXPORT).text, "Biedadvies")

    assert "- Richtbod:" not in bid
    assert "- Prijsstelling: marktconform, 2,5% korting" in bid


def test_a_house_sold_under_reservation_exports_conditions_and_the_note(client, listing_provider, llm_client):
    capture(client, listing_provider, raw_status="Verkocht onder voorbehoud")
    llm_client.verdict = model_says() | {"bid_advice": {"conditions": ["Reserveringslijst"]}}
    client.post(VERDICT)

    bid = section(client.get(EXPORT).text, "Biedadvies")

    assert "Verkocht onder voorbehoud" in bid
    assert "Reserveringslijst" in bid
    assert "- Openingsbod:" not in bid and "- Richtbod:" not in bid
    assert "haal vergelijkbare woningen op" not in bid


def test_without_the_profile_an_affordability_bound_richtbod_is_rounded_down(client, listing_provider, llm_client):
    poorer = typical_profile() | {"gross_annual_income": 30_000, "assets": {"savings": 5_000, "investments": 0}}
    capture(client, listing_provider, poorer)
    llm_client.verdict = lambda case, _: model_says(opening_bid=case["guide_bid"]["value"] - 1)
    guide = client.post(VERDICT).json()["bid_advice"]["guide_bid"]

    bid = section(client.get(f"{EXPORT}?profile=false").text, "Biedadvies")

    assert guide["capped_by"] == "walk_away_maximum"
    assert not mentions(bid, guide["value"])
    assert f"- Richtbod: € {guide['value'] // 5000 * 5000:,} (afgerond)".replace(",", ".") in bid


def test_the_export_gives_days_on_the_market_and_the_price_reduction_in_the_breakdown(
    client, listing_provider, llm_client
):
    # Listed at 625.000 150 days before the fetch, now asking 595.000.
    capture(client, listing_provider, price_history=(PricePoint(date="27 mei 2026", price=625_000),))
    llm_client.verdict = model_says(opening_bid=562_000)
    client.post(VERDICT)

    bid = section(client.get(EXPORT).text, "Biedadvies")

    assert "- Dagen te koop: 150 dagen, 2% korting op de verwachte verkoopprijs" in bid
    assert "- Prijsverlaging: van € 625.000 naar € 595.000, 1% korting op de verwachte verkoopprijs" in bid
    assert "- Samen 5,5% korting, naar beneden afgerond" in bid
    assert "Tempo onbekend" not in bid


def test_without_a_price_history_the_export_says_the_tempo_is_unknown(client, listing_provider, llm_client):
    capture(client, listing_provider, price_history=())
    llm_client.verdict = model_says(opening_bid=580_000)
    client.post(VERDICT)

    bid = section(client.get(EXPORT).text, "Biedadvies")

    assert "- Tempo onbekend: geen prijshistorie, dus geen korting voor dagen te koop of prijsverlaging" in bid
    assert "Dagen te koop" not in bid


@pytest.fixture
def renovation(settings, tmp_path, llm_client):
    cost_table = tmp_path / "renovation_costs.toml"
    cost_table.write_text(COST_TABLE)
    settings.renovation_costs_path = cost_table
    llm_client.observations = [
        {"key": "damp_or_mould", "value": True, "photos": [2], "note": "Vochtplek boven het raam"},
        {"key": "roof_condition", "value": "fair", "photos": [1], "note": "Dakpannen verkleurd"},
    ]


def test_the_renovation_estimate_is_exported_after_the_flags_with_exact_ranges(
    client, listing_provider, llm_client, renovation
):
    capture(client, listing_provider, living_area=None, brochure_url=None)
    llm_client.verdict = model_says()
    client.post(VERDICT)

    markdown = client.get(f"{EXPORT}?profile=false").text

    order = headings(markdown)
    assert order.index("## Verbouwingsraming") == order.index("## Signalen") + 1
    raming = section(markdown, "Verbouwingsraming")
    assert "kostentabel versie 7" in raming
    assert "### Direct nodig: € 2.000 – € 6.000 (midden € 4.000)" in raming
    assert "- Vochtprobleem verhelpen: € 2.000 – € 6.000 (geschat, prijspeil 2025, bron Testgids)" in raming
    assert "Vocht of schimmel zichtbaar: ja (Waarneming, geschat)" in raming
    assert "### Binnen 5 jaar: € 12.500 – € 23.500" in raming
    assert "woonoppervlak onbekend, middelgrote woning aangenomen" in raming
    assert "onderzoek op basis van bouwjaar" in raming
    assert "### Optioneel" not in raming
    assert "Niet meegenomen: geen Vragenlijst." in raming
    # The affordability effect of Direct nodig belongs to the Buyer Profile part only.
    assert "betaal" not in raming.lower()
    assert "afgetrokken" not in markdown and "na aftrek" not in markdown


def test_with_the_profile_the_direct_nodig_subtraction_shows_in_affordability_and_derivation(
    client, listing_provider, llm_client, renovation
):
    capture(client, listing_provider, living_area=None, brochure_url=None)
    llm_client.verdict = model_says()
    client.post(VERDICT)

    markdown = client.get(EXPORT).text

    assert "na aftrek van € 4.000 Direct nodig (Verbouwingsraming)" in section(markdown, "Kengetallen")
    assert "de verwachte verkoopprijs, min € 4.000 Direct nodig, plus 5%" in markdown
    assert "**Zwak onderbouwd**: de verwachte verkoopprijs rust op de WOZ-waarde" in markdown
    assert "Marge:" not in markdown
    # (595_000 - 4_000) x 1.05
    assert "Maximumbod: € 620.550" in markdown


def test_a_high_direct_nodig_flag_cites_its_midpoint_in_euros(client, listing_provider, settings, renovation):
    settings.renovation_costs_path.write_text(COST_TABLE.replace("low = 2000\nhigh = 6000", "low = 30000\nhigh = 50000"))
    capture(client, listing_provider, brochure_url=None)

    signalen = section(client.get(f"{EXPORT}?profile=false").text, "Signalen")

    assert "Direct nodig onderhoud (midden): € 40.000 (Berekend)" in signalen


def test_without_renovation_items_the_export_says_none_were_found(client, listing_provider, llm_client, renovation):
    llm_client.observations = []
    capture(client, listing_provider, construction_year=2015)

    raming = section(client.get(EXPORT).text, "Verbouwingsraming")

    assert "Geen verbouwingsposten gevonden" in raming


def test_a_hard_no_without_the_profile_does_not_print_the_deal_breaker(client, listing_provider):
    profile = typical_profile() | {"deal_breakers": ["Geen erfpacht"]}
    capture(client, listing_provider, profile, description="Appartement op erfpacht.")
    client.post(VERDICT)

    markdown = client.get(f"{EXPORT}?profile=false").text

    assert "Geen erfpacht" not in markdown
    assert "raakt een Deal-breaker uit het Koperprofiel" in section(markdown, "Oordeel")


def amount_forms(amount):
    """How a model may write an amount: "€ 412.345", "€412.345", "412.345", "€412k"."""
    dotted = f"{amount:,}".replace(",", ".")
    return [f"€ {dotted}", f"€{dotted}", dotted, f"€{round(amount / 1000)}k"]


def test_household_amounts_in_the_verdict_text_are_rounded_or_left_out(client, listing_provider, llm_client):
    capture(client, listing_provider, private_profile())
    affordability = client.get("/api/listings/80907644/case").json()["affordability"]
    maximum, monthly, equity = affordability["affordable_maximum"], affordability["monthly_cost"], affordability["equity"]
    forms = " / ".join(amount_forms(maximum))
    llm_client.verdict = model_says() | {
        "summary": f"Betaalbaar tot {forms}.",
        "reasoning": f"Maandlasten {amount_forms(monthly)[0]} per maand, overwaarde {amount_forms(equity)[1]}.",
        "bid_advice": {"opening_bid": 585_000, "conditions": [f"Niet boven {amount_forms(maximum)[0]}"]},
    }
    client.post(VERDICT)

    with_profile = client.get(EXPORT).text
    without = client.get(f"{EXPORT}?profile=false").text

    for markdown in (with_profile, without):
        for exact in (maximum, monthly, equity):
            assert not mentions(markdown, exact), exact
        assert f"{round(maximum / 1000)}k" not in markdown
    rounded = f"≈ € {round(maximum / 5000) * 5000:,}".replace(",", ".")
    assert f"Betaalbaar tot {rounded} / {rounded} / {rounded} / {rounded}." in with_profile
    assert f"Maandlasten ≈ € {round(monthly / 50) * 50:,} per maand".replace(",", ".") in with_profile
    assert f"Niet boven {rounded}" in with_profile
    assert "Betaalbaar tot [weggelaten] / [weggelaten] / [weggelaten] / [weggelaten]." in without
    assert "Maandlasten [weggelaten] per maand, overwaarde [weggelaten]." in without
    assert "Niet boven [weggelaten]" in without


def test_without_the_profile_affordability_bound_bids_are_rounded_down(client, listing_provider, llm_client):
    poorer = typical_profile() | {"gross_annual_income": 30_000, "assets": {"savings": 5_000, "investments": 0}}
    capture(client, listing_provider, poorer)
    def says(case, _):
        opening = case["guide_bid"]["value"] - 1
        return model_says(opening_bid=opening) | {"reasoning": f"Open op {amount_forms(opening)[0]}."}

    llm_client.verdict = says
    advice = client.post(VERDICT).json()["bid_advice"]
    maximum, opening = advice["walk_away_maximum"], advice["opening_bid"]

    without = client.get(f"{EXPORT}?profile=false").text
    bid = section(without, "Biedadvies")

    assert not mentions(without, opening)
    bid_with_profile = section(client.get(EXPORT).text, "Biedadvies")

    assert not mentions(bid, maximum)
    assert not mentions(bid, opening)
    assert f"Maximumbod: € {maximum // 5000 * 5000:,} (afgerond)".replace(",", ".") in bid
    assert f"Openingsbod: € {opening // 5000 * 5000:,} (afgerond)".replace(",", ".") in bid
    assert "Direct nodig" not in bid
    assert f"Openingsbod: € {opening:,}\n".replace(",", ".") in bid_with_profile


def test_kosten_koper_is_rounded(client, listing_provider):
    capture(client, listing_provider, private_profile())
    total = client.get("/api/listings/80907644/case").json()["affordability"]["kosten_koper"]["total"]

    markdown = client.get(EXPORT).text

    assert not mentions(markdown, total)
    assert f"Kosten koper bij de verwachte verkoopprijs: ≈ € {round(total / 5000) * 5000:,}".replace(",", ".") in markdown


def test_the_header_prints_the_prompt_version_the_verdict_was_made_with(
    client, listing_provider, llm_client, monkeypatch
):
    capture(client, listing_provider)
    llm_client.verdict = model_says()
    verdict = client.post(VERDICT).json()
    monkeypatch.setattr("app.assembly.VERDICT_PROMPT_VERSION", VERDICT_PROMPT_VERSION + 1)

    markdown = client.get(EXPORT).text

    assert verdict["prompt_version"] == VERDICT_PROMPT_VERSION
    assert f"Promptversie Oordeel: {VERDICT_PROMPT_VERSION}\n" in markdown


def test_an_older_verdict_without_a_prompt_version_prints_onbekend(client, listing_provider, llm_client, settings):
    capture(client, listing_provider)
    llm_client.verdict = model_says()
    verdict = client.post(VERDICT).json()
    # A Verdict stored before the prompt version was recorded.
    older = {k: v for k, v in verdict.items() if k not in ("id", "version", "created_at", "prompt_version")}
    store.add_verdict(settings.database_path, "80907644", verdict["created_at"], older)

    assert "Promptversie Oordeel: onbekend" in client.get(EXPORT).text


def test_the_header_names_the_cost_table_version_and_the_legend_the_renovation_estimate(
    client, listing_provider, renovation
):
    capture(client, listing_provider)

    markdown = client.get(EXPORT).text

    assert "- Versie kostentabel verbouwing: 7" in section(markdown, "Herkomst van dit dossier")
    assert "- Verbouwingsraming = Renovation Estimate" in markdown


def test_boiler_and_wiring_findings_have_dutch_labels(client, listing_provider, llm_client):
    llm_client.findings = [
        {"topic": "boiler_old", "present": True, "statement": "Ketel uit 2005.", "quote": "Ligging en indeling", "page": 2},
        {"topic": "wiring_old", "present": True, "statement": "Oude groepenkast.", "quote": "Ligging en indeling", "page": 2},
    ]
    capture(client, listing_provider)

    facts = section(client.get(EXPORT).text, "Feiten")

    assert "- Cv-ketel oud (van toepassing): Ketel uit 2005." in facts
    assert "- Elektra oud (van toepassing): Oude groepenkast." in facts


def test_monthly_costs_are_exported_net_with_gross_beside_them(client, listing_provider, llm_client):
    """Typical household at the asking price: €1.935 gross, €1.461 net of hypotheekrenteaftrek."""
    capture(client, listing_provider, typical_profile())
    llm_client.verdict = model_says()
    client.post(VERDICT)

    markdown = client.get(EXPORT).text

    assert "Maandlasten bij de verwachte verkoopprijs: ≈ € 1.450 per maand netto (≈ € 1.950 per maand bruto)" in markdown


def kengetallen(markdown: str) -> str:
    return markdown.split("## Kengetallen")[1].split("\n## ")[0]


def test_the_expected_sale_price_and_prijsstelling_are_exported_with_their_basis(
    client, listing_provider, source_clients
):
    capture(client, listing_provider)
    source_clients["comparables"].facts = SEVERAL
    client.post(FETCH_COMPARABLES)

    section = kengetallen(client.get(EXPORT).text)

    # 608.000 by comparables plus NVM's 4,6% average overbid; the asking price is 595.000.
    assert "- Verwachte verkoopprijs: € 635.968 (bandbreedte € " in section
    assert "op basis van 5 vergelijkbare woningen, incl. 4,6% gemiddeld overbod" in section
    assert "- Prijsstelling: vraagprijs 6,4% onder verwachte verkoopprijs: laag ingezet" in section
    assert "Zwak onderbouwd" not in section


def test_a_weakly_grounded_expected_sale_price_says_so(client, listing_provider):
    capture(client, listing_provider)

    section = kengetallen(client.get(EXPORT).text)

    assert "- Verwachte verkoopprijs: € 595.000 (op basis van de WOZ-waarde; zwak onderbouwd)" in section
    assert "- Prijsstelling: vraagprijs gelijk aan verwachte verkoopprijs: marktconform" in section


def test_without_an_expected_sale_price_the_export_says_how_to_get_one(client, listing_provider, source_clients):
    source_clients["woz"].at_asking_price = False
    capture(client, listing_provider)

    section = kengetallen(client.get(EXPORT).text)

    assert "- Verwachte verkoopprijs: onbekend (haal vergelijkbare woningen op)" in section
    assert "Prijsstelling" not in section


def dotted(amount: int) -> str:
    return f"{amount:,}".replace(",", ".")


def with_debts() -> dict:
    return {
        **typical_profile(),
        "debts": [
            {"kind": "study_loan", "debt": 30_000, "interest_rate": 0.025, "stelsel": "SF35"},
            {"kind": "revolving_credit", "limit": 5_000},
        ],
    }


def test_the_dossier_and_export_list_debts_by_kind_with_their_toetslast_rounded(client, listing_provider):
    capture(client, listing_provider, with_debts())
    debts = client.get("/api/listings/80907644/case").json()["affordability"]["debts"]
    # €107,25 (DUO, 35 years at 2,5%) and 2% of €5.000.
    assert [(d["kind"], d["toetslast"]) for d in debts] == [("study_loan", 107.25), ("revolving_credit", 100.0)]
    assert all(d["leenruimte_cost"] > 0 for d in debts)

    markdown = client.get(EXPORT).text

    study, credit = (round(d["leenruimte_cost"] / 5000) * 5000 for d in debts)
    assert f"    - Studieschuld: ≈ € 100 per maand, kost ≈ € {dotted(study)} leenruimte" in markdown
    assert f"    - Doorlopend krediet: ≈ € 100 per maand, kost ≈ € {dotted(credit)} leenruimte" in markdown
    assert not mentions(markdown, debts[0]["leenruimte_cost"])


def test_without_the_profile_no_debts_are_exported(client, listing_provider):
    capture(client, listing_provider, with_debts())

    markdown = client.get(EXPORT, params={"profile": "false"}).text

    assert "Studieschuld" not in markdown
    assert "Doorlopend krediet" not in markdown
@pytest.mark.parametrize("query", ["", "?profile=false"])
def test_the_rate_per_route_is_named_with_its_source_and_an_own_rate_rounded(client, listing_provider, query):
    """An own rate is household data: 4,23% is exported as 4,2%. The market rate is not, so exact."""
    capture(client, listing_provider, typical_profile() | {"offered_rate_nhg": 0.0423})

    markdown = client.get(f"{EXPORT}{query}").text

    herkomst = markdown.split("## Herkomst van dit dossier")[1].split("\n## ")[0]
    assert "- Hypotheekrente met NHG: eigen rente ≈ 4,2%" in herkomst
    assert "- Hypotheekrente zonder NHG: marktrente 4,78% (2026-11-02)" in herkomst
    assert "4,23" not in markdown and "0.0423" not in markdown
