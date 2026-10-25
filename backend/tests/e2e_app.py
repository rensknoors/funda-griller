"""App wired to fakes and a temp SQLite file, served to the Playwright smoke test."""

import base64
import tempfile
from pathlib import Path

from app.main import create_app
from app.ports import Ports, ProviderBlocked, SourceFact, SourceSkipped
from app.settings import Settings
from tests.conftest import SOURCES
from tests.fakes import (
    FakeDocumentDownloader,
    FakeGeocoder,
    FakeListingProvider,
    FakeLlmClient,
    FakePhotoDownloader,
    FakeSourceClient,
    FakeTravelTimeRouter,
)
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import make_pdf

BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/"
# Available on first fetch, sold on every refetch after: the comparison view's status change.
CHANGING_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-markt-3/55500001/"

_data_dir = Path(tempfile.mkdtemp(prefix="funda-griller-e2e-"))

_listing_provider = FakeListingProvider()
_listing_provider.listings[LIVE_URL] = live_listing()
_listing_provider.listings[BLOCKED_URL] = ProviderBlocked(BLOCKED_URL)
# Its own woning, so fetching comparables and an Oordeel here leaves the other specs' woning alone.
COMPARABLES_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-40/80907650/"
_listing_provider.listings[COMPARABLES_URL] = live_listing(
    funda_id="80907650", provider_id="17270380", url=COMPARABLES_URL, address="Dorpsstraat 40"
)
_markt = dict(
    funda_id="55500001",
    provider_id="55500001",
    url=CHANGING_URL,
    address="Markt 3",
    city="Maastricht",
    asking_price=425_000,
    living_area=80,
    plot_area=None,
    rooms=3,
    bedrooms=2,
    construction_year=1965,
    energy_label="C",
    description="Appartement met balkon.",
    price_history=(),
    photo_urls=(),
    brochure_url=None,
)
_listing_provider.listings[CHANGING_URL] = [
    live_listing(**_markt),
    live_listing(**_markt, raw_status="Verkocht"),
]

_source_clients = {name: FakeSourceClient(name) for name in SOURCES}
_source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
_source_clients["woz"].facts = [
    SourceFact("woz_value", 371_000, "2024-01-01"),
    SourceFact("woz_value", 392_000, "2025-01-01"),
]
_source_clients["flood_soil"].facts = [
    SourceFact("flood_depth_m", 0.88, "2026-01-28"),
    SourceFact("subsidence_mm_per_year", 1.5, "2026-06-23"),
    SourceFact("pile_rot_risk_pct", 2.1),
]
_source_clients["noise"].error = SourceSkipped("no_coordinates")
# Fetched only when the user asks. Per m²: 4000, 4200, 4400 -> median 4200.
_source_clients["comparables"].facts = [
    SourceFact(
        "comparable",
        {
            "funda_id": funda_id,
            "address": address,
            "city": "Holtum",
            "asking_price": price,
            "living_area": area,
            "raw_status": "Verkocht",
            "recently_sold": True,
            "url": f"https://www.funda.nl/detail/koop/holtum/huis/{funda_id}/",
        },
    )
    for funda_id, address, price, area in (
        ("80900001", "Dorpsstraat 3", 500_000, 125),
        ("80900002", "Kerkstraat 8", 630_000, 150),
        ("80900003", "Molenweg 21", 550_000, 125),
    )
]


def _rate(case: dict, _profile: dict) -> dict:
    """A plausible Verdict derived from the Case, so it always passes validation."""
    asking = next(f["value"] for f in case["facts"] if f["key"] == "asking_price")
    affordable = case["affordability"]["affordable_maximum"]
    cited = [flag["id"] for flag in case["flags"]]
    if affordable < asking:
        return {
            "tier": "skip",
            "summary": "Buiten je betaalruimte.",
            "reasoning": "De vraagprijs ligt boven wat jullie kunnen betalen.",
            "cited_flags": cited,
            "bid_advice": None,
        }
    limits = case["bid_limits"]
    walk_away = min(affordable, limits["comparables_maximum"] or affordable, asking + 20_000)
    return {
        "tier": "consider",
        "summary": "Degelijke woning, de vraagprijs is aan de hoge kant.",
        "reasoning": "De woning past bij jullie wensen, maar de vraagprijs ligt ver boven de "
        "WOZ-waarde. Die WOZ komt van een derde partij en is onofficieel.",
        "cited_flags": cited,
        "bid_advice": {
            "opening_bid": min(walk_away, asking - 15_000),
            "walk_away_maximum": walk_away,
            "conditions": ["Financieringsvoorbehoud", "Bouwkundige keuring"],
        },
    }


def _findings(document_path: str) -> list[dict]:
    """Findings keyed off the generated PDFs' text: the Vragenlijst discloses asbestos, the
    brochure says what stays."""
    content = Path(document_path).read_bytes()
    if b"asbest" in content:
        return [
            {
                "topic": "asbestos",
                "present": True,
                "statement": "Asbest in de dakplaten van de schuur.",
                "quote": "Ja, in de dakplaten van de schuur.",
                "page": 2,
            }
        ]
    if b"Brochure" in content:
        return [
            {
                "topic": "stays_or_goes",
                "present": True,
                "statement": "De gordijnen blijven achter.",
                "quote": "De gordijnen blijven achter.",
                "page": 2,
            }
        ]
    return []


_llm_client = FakeLlmClient()
_llm_client.verdict = _rate
_llm_client.findings = _findings
_document_downloader = FakeDocumentDownloader(make_pdf(["Brochure Buchterweg 15", "De gordijnen blijven achter."]))
# Observations that raise no Flag, so the other specs' Signaal counts stay as they are.
_llm_client.observations = [
    {"key": "kitchen_age_years", "value": 12, "photos": [2], "note": "Lichte keuken met moderne fronten"},
    {"key": "roof_condition", "value": "fair", "photos": [1], "note": "Dakpannen deels verkleurd"},
]

# A 1x1 PNG for every Listing photo, so the browser renders real images.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_photo_downloader = FakePhotoDownloader()
_photo_downloader.photos = {url: _PNG for url in live_listing().photo_urls}

# Commute: one office, 52 minutes by car and 140 by bike from any woning. Only profiles with a
# commute destination run it; the other specs' profiles have none, so it is skipped there.
_geocoder = FakeGeocoder()
_geocoder.places = {"Kantoorlaan 1, Eindhoven": (51.44, 5.47)}
_router = FakeTravelTimeRouter()
_router.minutes = {("car", (51.44, 5.47)): 52.0, ("bike", (51.44, 5.47)): 140.0}
# Its own woning, so the commute spec's Signaal leaves the other specs' counts alone.
COMMUTE_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-41/80907651/"
_listing_provider.listings[COMMUTE_URL] = live_listing(
    funda_id="80907651", provider_id="17270381", url=COMMUTE_URL, address="Dorpsstraat 41"
)

app = create_app(
    Settings(
        _env_file=None,
        database_path=_data_dir / "e2e.sqlite",
        media_dir=_data_dir / "media",
    ),
    Ports(
        listing_provider=_listing_provider,
        source_clients=_source_clients,
        llm_client=_llm_client,
        photo_downloader=_photo_downloader,
        document_downloader=_document_downloader,
        geocoder=_geocoder,
        router=_router,
    ),
)
