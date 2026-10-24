"""App wired to fakes and a temp SQLite file, served to the Playwright smoke test."""

import tempfile
from pathlib import Path

from app.main import create_app
from app.ports import Ports, ProviderBlocked
from app.settings import Settings
from tests.conftest import SOURCES
from tests.fakes import FakeListingProvider, FakeLlmClient, FakeSourceClient
from tests.listing_fixtures import LIVE_URL, live_listing

BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/"

_data_dir =Path(tempfile.mkdtemp(prefix="funda-griller-e2e-"))

_listing_provider = FakeListingProvider()
_listing_provider.listings[LIVE_URL] = live_listing()
_listing_provider.listings[BLOCKED_URL] = ProviderBlocked(BLOCKED_URL)

app = create_app(
    Settings(
        _env_file=None,
        database_path=_data_dir / "e2e.sqlite",
        media_dir=_data_dir / "media",
    ),
    Ports(
        listing_provider=_listing_provider,
        source_clients={name: FakeSourceClient(name) for name in SOURCES},
        llm_client=FakeLlmClient(),
    ),
)
