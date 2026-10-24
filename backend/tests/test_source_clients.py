import pytest
from funda.exceptions import PriceHistoryError
from funda.listing import PriceChange, PriceHistory

from app.ports import SourceFact, SourceFailed, SourceSkipped
from app.source_clients import EpOnlineEnergielabelSource, PyfundaWozSource
from tests import pyfunda_fixtures as fx
from tests.listing_fixtures import live_listing

# Shaped like one PandEnergielabelV5 item from the EP-Online v5 API.
EP_ONLINE_LABEL = {
    "Energieklasse": "A",
    "Registratiedatum": "2021-06-14T00:00:00",
    "Opnamedatum": "2021-06-10T00:00:00",
    "Geldig_tot": "2031-06-14T00:00:00",
}


class FakeHttp:
    def __init__(self, status: int, payload: object = None) -> None:
        self.status = status
        self.payload = payload
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict) -> tuple[int, object]:
        self.requests.append((url, headers))
        return self.status, self.payload


def addressed(**overrides):
    return live_listing(postcode="6118 AB", house_number="15", **overrides)


def test_energielabel_is_looked_up_by_postcode_and_house_number():
    http = FakeHttp(200, [EP_ONLINE_LABEL])

    facts = EpOnlineEnergielabelSource("key-1", http).fetch(addressed(house_number_suffix="a"))

    assert facts == [SourceFact(name="energy_label", value="A", as_of="2021-06-14")]
    [(url, headers)] = http.requests
    assert url == (
        "https://public.ep-online.nl/api/v5/PandEnergielabel/Adres"
        "?postcode=6118AB&huisnummer=15&huisletter=a"
    )
    assert headers == {"Authorization": "key-1"}


def test_energielabel_without_a_registered_label_has_no_facts():
    assert EpOnlineEnergielabelSource("key-1", FakeHttp(404)).fetch(addressed()) == []


def test_energielabel_is_skipped_without_api_key_or_address():
    with pytest.raises(SourceSkipped, match="no_api_key"):
        EpOnlineEnergielabelSource(None, FakeHttp(200, [])).fetch(addressed())
    with pytest.raises(SourceSkipped, match="no_address"):
        EpOnlineEnergielabelSource("key-1", FakeHttp(200, [])).fetch(live_listing())


def test_energielabel_register_errors_are_failures():
    with pytest.raises(SourceFailed):
        EpOnlineEnergielabelSource("key-1", FakeHttp(401)).fetch(addressed())


def test_woz_values_come_from_the_price_history():
    history = PriceHistory(
        status="ok",
        changes=(
            PriceChange(price=595000, status="asking_price", date="2026-10-21"),
            PriceChange(price=392000, status="woz", date="2025-01-01"),
            PriceChange(price=371000, status="woz", date="2024-01-01"),
        ),
    )
    client = fx.FakePyfundaClient(fx.live_listing(), history)

    facts = PyfundaWozSource(client).fetch(live_listing())

    assert facts == [
        SourceFact(name="woz_value", value=371000, as_of="2024-01-01"),
        SourceFact(name="woz_value", value=392000, as_of="2025-01-01"),
    ]


def test_unavailable_price_history_is_a_failure():
    client = fx.FakePyfundaClient(fx.live_listing(), history_error=PriceHistoryError("down"))

    with pytest.raises(SourceFailed):
        PyfundaWozSource(client).fetch(live_listing())
