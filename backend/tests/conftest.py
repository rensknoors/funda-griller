import socket
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.ports import Ports
from app.settings import Settings
from tests.fakes import (
    FakeClock,
    FakeDocumentDownloader,
    FakeListingProvider,
    FakeLlmClient,
    FakePhotoDownloader,
    FakeSourceClient,
)
from tests.pdf_fixtures import make_pdf

SOURCES = ("energielabel", "woz", "flood_soil", "noise", "comparables")


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        database_path=tmp_path / "test.sqlite",
        media_dir=tmp_path / "media",
    )


@pytest.fixture
def listing_provider():
    return FakeListingProvider()


@pytest.fixture
def source_clients():
    return {name: FakeSourceClient(name) for name in SOURCES}


@pytest.fixture
def llm_client():
    return FakeLlmClient()


@pytest.fixture
def photo_downloader():
    return FakePhotoDownloader()


@pytest.fixture
def document_downloader():
    return FakeDocumentDownloader(make_pdf(["Brochure", "Ligging en indeling"]))


@pytest.fixture
def clock():
    return FakeClock(datetime(2026, 10, 24, 12, 0, tzinfo=UTC))


@pytest.fixture
def client(
    settings, listing_provider, source_clients, llm_client, photo_downloader, document_downloader, clock
):
    ports = Ports(
        listing_provider=listing_provider,
        source_clients=source_clients,
        llm_client=llm_client,
        photo_downloader=photo_downloader,
        document_downloader=document_downloader,
    )
    with TestClient(create_app(settings, ports, clock)) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise RuntimeError("network access is not allowed in tests")

    monkeypatch.setattr(socket.socket, "connect", refuse)
