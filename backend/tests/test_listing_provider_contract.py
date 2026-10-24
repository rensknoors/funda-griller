"""Contract every Listing provider adapter meets: `fetch(url) -> Listing`, same shape, same errors."""

import dataclasses
import json

import pytest

from app.manual_provider import ManualEntry, ManualListingProvider
from app.ports import InvalidListingUrl, Listing, ListingProvider
from app.pyfunda_provider import PyfundaListingProvider
from tests import pyfunda_fixtures as fx

LIVE_URL = fx.LIVE_URL


def pyfunda_adapter() -> ListingProvider:
    return PyfundaListingProvider(fx.FakePyfundaClient(fx.live_listing(), fx.live_price_history()))


def manual_adapter() -> ListingProvider:
    """The same house as the pyfunda fixture, as the user would type it in."""
    return ManualListingProvider(
        ManualEntry(
            raw_status="Beschikbaar",
            address="Buchterweg 15",
            city="Holtum",
            asking_price=595000,
            living_area=152,
            plot_area=410,
            rooms=6,
            bedrooms=4,
            construction_year=1931,
            energy_label="B",
            heating="Warmtepomp",
            description="Vrijstaande woning met garage.",
            photo_urls=("/api/listings/80907644/photos/1.jpg",),
        )
    )


ADAPTERS = pytest.mark.parametrize("make_adapter", [pyfunda_adapter, manual_adapter])


@ADAPTERS
def test_fetch_returns_a_listing_keyed_on_the_url_id(make_adapter):
    listing = make_adapter().fetch(LIVE_URL)

    assert isinstance(listing, Listing)
    assert listing.funda_id == "80907644"
    assert listing.url == LIVE_URL


@ADAPTERS
def test_fetch_carries_the_core_listing_facts(make_adapter):
    listing = make_adapter().fetch(LIVE_URL)

    assert listing.raw_status == "Beschikbaar"
    assert (listing.address, listing.city) == ("Buchterweg 15", "Holtum")
    assert listing.asking_price == 595000
    assert (listing.living_area, listing.plot_area) == (152, 410)
    assert (listing.rooms, listing.bedrooms) == (6, 4)
    assert listing.construction_year == 1931
    assert listing.energy_label == "B"
    assert listing.heating == "Warmtepomp"
    assert listing.description == "Vrijstaande woning met garage."
    assert len(listing.photo_urls) >= 1


@ADAPTERS
def test_fetched_listing_serialises(make_adapter):
    listing = make_adapter().fetch(LIVE_URL)

    dumped = json.loads(json.dumps(dataclasses.asdict(listing)))
    assert dumped["asking_price"] == 595000


@ADAPTERS
def test_non_funda_url_is_invalid(make_adapter):
    with pytest.raises(InvalidListingUrl):
        make_adapter().fetch("https://example.com/huis/1")
