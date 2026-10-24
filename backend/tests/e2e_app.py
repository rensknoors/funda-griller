"""App wired to fakes and a temp SQLite file, served to the Playwright smoke test."""

import tempfile
from pathlib import Path

from app.main import create_app
from app.ports import Ports, ProviderBlocked, SourceFact, SourceSkipped
from app.settings import Settings
from tests.conftest import SOURCES
from tests.fakes import FakeListingProvider, FakeLlmClient, FakeSourceClient
from tests.listing_fixtures import LIVE_URL, live_listing

BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/"

_data_dir =Path(tempfile.mkdtemp(prefix="funda-griller-e2e-"))

_listing_provider = FakeListingProvider()
_listing_provider.listings[LIVE_URL] = live_listing()
_listing_provider.listings[BLOCKED_URL] = ProviderBlocked(BLOCKED_URL)

_source_clients = {name: FakeSourceClient(name) for name in SOURCES}
_source_clients["energielabel"].facts = [SourceFact("energy_label", "A", "2021-06-14")]
_source_clients["woz"].facts = [
    SourceFact("woz_value", 371_000, "2024-01-01"),
    SourceFact("woz_value", 392_000, "2025-01-01"),
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


_llm_client = FakeLlmClient()
_llm_client.verdict = _rate

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
    ),
)
