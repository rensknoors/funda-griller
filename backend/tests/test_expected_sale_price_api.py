"""Expected Sale Price and Prijsstelling in the Case: what the house is expected to sell for, from
evidence independent of its own asking price, and how the seller priced it against that."""

import pytest

from app.ports import SourceFact

from tests.listing_fixtures import LIVE_URL, live_listing
from tests.test_comparables_api import FETCH_COMPARABLES, NOW, NVM, SEVERAL, comparable

CASE = "/api/listings/80907644/case"
WOZ = [SourceFact(name="woz_value", value=392_000, as_of="2025-01-01")]
# CBS house price index brings 392.000 (peildatum 2025-01) to 420.289 in 2026-10.
INDEXED_WOZ = 420_289
# Price per m² 3000..5000 with a median of 4000: 152 m² is worth 608.000, the interquartile range
# runs from 3500 to 4500 per m².
SPREAD = [comparable(str(i), price * 10_000, 100) for i, price in zip(range(101, 106), (30, 35, 40, 45, 50))]


def capture(client, listing_provider, **overrides):
    listing_provider.listings[LIVE_URL] = live_listing(**overrides)
    client.post("/api/listings", json={"url": LIVE_URL})


def metrics(client, listing_provider, source_clients, comparables=None, woz=None, **overrides):
    if woz:
        source_clients["woz"].facts = woz
    capture(client, listing_provider, **overrides)
    if comparables is not None:
        source_clients["comparables"].facts = comparables
        client.post(FETCH_COMPARABLES)
    return client.get(CASE).json()["metrics"]


def test_sufficient_comparables_plus_the_average_overbid_are_the_expected_sale_price(
    client, listing_provider, source_clients
):
    expected = metrics(client, listing_provider, source_clients, comparables=SPREAD, woz=WOZ)[
        "expected_sale_price"
    ]

    assert expected == {
        "value": 635_968,
        "basis": "comparables",
        "weakly_grounded": False,
        "overbid": {"value": 0.046, "house_type": None, "source": NVM, "period": "2e kwartaal 2026"},
        "low": 556_472,
        "high": 715_464,
        "provenance": "computed",
        "computed_at": NOW,
    }


def test_the_overbid_follows_the_soort_woning(client, listing_provider, source_clients):
    expected = metrics(
        client, listing_provider, source_clients, comparables=SPREAD, house_type="Eengezinswoning, tussenwoning"
    )["expected_sale_price"]

    assert expected["overbid"]["value"] == 0.059
    assert expected["overbid"]["house_type"] == "tussenwoning"
    assert expected["value"] == 643_872


def test_thin_comparables_do_not_count_and_the_indexed_woz_value_is_used(
    client, listing_provider, source_clients
):
    expected = metrics(client, listing_provider, source_clients, comparables=SEVERAL[:1], woz=WOZ)[
        "expected_sale_price"
    ]

    assert expected["value"] == INDEXED_WOZ
    assert expected["basis"] == "woz"
    assert expected["weakly_grounded"] is True
    assert expected["overbid"] is None
    assert expected["low"] is None
    assert expected["high"] is None


def test_the_raw_woz_value_is_used_when_its_peildatum_is_outside_the_index(
    client, listing_provider, source_clients
):
    old = [SourceFact(name="woz_value", value=300_000, as_of="2014-01-01")]

    expected = metrics(client, listing_provider, source_clients, woz=old)["expected_sale_price"]

    assert (expected["value"], expected["basis"]) == (300_000, "woz")


def test_the_woz_basis_works_without_an_asking_price(client, listing_provider, source_clients):
    all_metrics = metrics(client, listing_provider, source_clients, woz=WOZ, asking_price=None)

    assert all_metrics["expected_sale_price"]["value"] == INDEXED_WOZ
    assert all_metrics["asking_vs_expected"] is None


@pytest.mark.parametrize("comparables", [None, [], SEVERAL[:1]])
def test_with_neither_sufficient_comparables_nor_woz_there_is_no_expected_sale_price(
    client, listing_provider, source_clients, comparables
):
    """The asking price is never a fallback."""
    all_metrics = metrics(client, listing_provider, source_clients, comparables=comparables)

    expected = all_metrics["expected_sale_price"]
    assert expected["value"] is None
    assert expected["basis"] is None
    assert expected["weakly_grounded"] is None
    assert all_metrics["asking_vs_expected"] is None


@pytest.mark.parametrize(
    ("asking_price", "difference", "label"),
    [
        (441_303, 21_014, "marktconform"),  # +4,99992%: inside the band
        (441_304, 21_015, "hoog ingezet"),  # just beyond +5%
        (399_275, -21_014, "marktconform"),  # -4,99996%
        (399_274, -21_015, "laag ingezet"),  # just beyond -5%
        (INDEXED_WOZ, 0, "marktconform"),
    ],
)
def test_prijsstelling_is_labelled_at_the_band_edges(
    client, listing_provider, source_clients, asking_price, difference, label
):
    asking_vs_expected = metrics(
        client, listing_provider, source_clients, woz=WOZ, asking_price=asking_price
    )["asking_vs_expected"]

    assert asking_vs_expected["asking_price"] == asking_price
    assert asking_vs_expected["expected_sale_price"] == INDEXED_WOZ
    assert asking_vs_expected["difference"] == difference
    assert asking_vs_expected["prijsstelling"] == label
    assert asking_vs_expected["band"] == 0.05
    assert asking_vs_expected["provenance"] == "computed"


def test_the_prijsstelling_percentage_is_rounded_to_one_decimal(client, listing_provider, source_clients):
    asking_vs_expected = metrics(
        client, listing_provider, source_clients, comparables=SPREAD, woz=WOZ
    )["asking_vs_expected"]

    # Asking 595.000 against 635.968.
    assert asking_vs_expected["difference"] == -40_968
    assert asking_vs_expected["percent"] == -6.4
    assert asking_vs_expected["prijsstelling"] == "laag ingezet"


def test_the_prijsstelling_band_is_configurable(client, listing_provider, source_clients, settings):
    settings.prijsstelling_band = 0.10

    asking_vs_expected = metrics(
        client, listing_provider, source_clients, comparables=SPREAD, woz=WOZ
    )["asking_vs_expected"]

    assert asking_vs_expected["band"] == 0.10
    assert asking_vs_expected["prijsstelling"] == "marktconform"
