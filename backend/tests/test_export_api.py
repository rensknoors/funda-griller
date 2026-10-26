"""Markdown export (Exporteer als Markdown), through the HTTP API: one Dutch `.md` file holding a
house's Case and current Verdict, for pasting into another LLM chat. The Buyer Profile part is
always anonymised and can be left out."""

import re

import pytest

from app.ports import SourceFact
from tests.fakes import FakeGeocoder, FakeTravelTimeRouter
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.profile_fixtures import typical_profile

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
    assert "Promptversie Oordeel: 3" in markdown
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
    assert "Erfpacht (van toepassing): Erfpacht afgekocht tot 2050. (door verkoper, Brochure (funda), p. 2)" in facts
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
    for exact in (exact_home_equity, affordability["affordable_maximum"], affordability["headroom"], affordability["monthly_cost"]):
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
    llm_client.verdict = lambda case, _: model_says(opening_bid=case["walk_away"]["walk_away_maximum"] - 10_000)
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
