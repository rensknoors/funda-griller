"""App wired to fakes and a temp SQLite file, served to the Playwright smoke test."""

import tempfile
from pathlib import Path

from app.main import create_app
from app.ports import Ports, ProviderBlocked, SourceFact, SourceSkipped
from app.settings import Settings
from tests.conftest import SOURCES
from tests.fakes import FakeDocumentDownloader, FakeListingProvider, FakeLlmClient, FakeSourceClient
from tests.listing_fixtures import LIVE_URL, live_listing
from tests.pdf_fixtures import make_pdf

BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/"
# Available on first fetch, sold on every refetch after: the comparison view's status change.
CHANGING_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-markt-3/55500001/"

_data_dir = Path(tempfile.mkdtemp(prefix="funda-griller-e2e-"))

_listing_provider = FakeListingProvider()
_listing_provider.listings[LIVE_URL] = live_listing()
_listing_provider.listings[BLOCKED_URL] = ProviderBlocked(BLOCKED_URL)
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


def _rate(case: dict, _profile: dict) -> dict:
    """A plausible Verdict derived from the Case, so it always passes validation."""
    asking = next(f["value"] for f in case["facts"] if f["key"] == "asking_price")
    affordable = case["affordability"]["max_price"]
    cited = [flag["id"] for flag in case["flags"]]
    if affordable < asking:
        return {
            "tier": "skip",
            "summary": "Buiten je betaalruimte.",
            "reasoning": "De vraagprijs ligt boven wat jullie kunnen betalen.",
            "cited_flags": cited,
            "bid_advice": None,
        }
    walk_away = min(affordable, asking + 20_000)
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
        return [{"topic": "asbestos", "present": True, "statement": "Asbest in de dakplaten van de schuur.", "page": 2}]
    if b"Brochure" in content:
        return [{"topic": "stays_or_goes", "present": True, "statement": "De gordijnen blijven achter.", "page": 2}]
    return []


_llm_client = FakeLlmClient()
_llm_client.verdict = _rate
_llm_client.findings = _findings
_document_downloader = FakeDocumentDownloader(make_pdf(["Brochure Buchterweg 15", "De gordijnen blijven achter."]))

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
        document_downloader=_document_downloader,
    ),
)
