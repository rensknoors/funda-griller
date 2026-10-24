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
_source_clients["flood_soil"].facts = [
    SourceFact("flood_depth_m", 0.88, "2026-01-28"),
    SourceFact("subsidence_mm_per_year", 1.5, "2026-06-23"),
    SourceFact("pile_rot_risk_pct", 2.1),
]
_source_clients["noise"].error = SourceSkipped("no_coordinates")

app = create_app(
    Settings(
        _env_file=None,
        database_path=_data_dir / "e2e.sqlite",
        media_dir=_data_dir / "media",
    ),
    Ports(
        listing_provider=_listing_provider,
        source_clients=_source_clients,
        llm_client=FakeLlmClient(),
    ),
)
