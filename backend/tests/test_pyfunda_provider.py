import dataclasses
import json

import pytest
from funda.exceptions import (
    FingerprintError,
    FundaRequestError,
    ListingNotFound,
    PriceHistoryError,
)

from funda.listing import Media

from app.ports import InvalidListingUrl, ListingRemoved, ProviderBlocked
from app.pyfunda_provider import PyfundaListingProvider
from tests import pyfunda_fixtures as fx


def test_live_listing_is_normalised():
    client = fx.FakePyfundaClient(fx.live_listing(), fx.live_price_history())

    listing = PyfundaListingProvider(client).fetch(fx.LIVE_URL)

    assert listing.funda_id == "80907644"
    assert listing.provider_id == "17270371"
    assert listing.raw_status == "Beschikbaar"
    assert (listing.address, listing.city) == ("Buchterweg 15", "Holtum")
    assert (listing.postcode, listing.house_number, listing.house_number_suffix) == ("6118 AB", "15", "a")
    assert listing.asking_price == 595000
    assert (listing.living_area, listing.plot_area) == (152, 410)
    assert (listing.rooms, listing.bedrooms) == (6, 4)
    assert listing.construction_year == 1931
    assert listing.energy_label == "B"
    assert (listing.latitude, listing.longitude) == (51.0, 5.8)
    assert listing.heating == "Warmtepomp"
    assert listing.photo_urls == ("https://cloud.funda.nl/p1.jpg", "https://cloud.funda.nl/p2.jpg")
    assert listing.brochure_url == "https://cloud.funda.nl/brochure.pdf"


def test_price_history_keeps_asking_prices_only():
    client = fx.FakePyfundaClient(fx.live_listing(), fx.live_price_history())

    listing = PyfundaListingProvider(client).fetch(fx.LIVE_URL)

    assert [(p.date, p.price) for p in listing.price_history] == [("2026-10-21", 595000)]


def test_sold_listing_with_bare_attributes_parses_and_reads_status_from_characteristics():
    client = fx.FakePyfundaClient(fx.sold_listing(), history_error=PriceHistoryError())

    listing = PyfundaListingProvider(client).fetch(fx.SOLD_URL)

    assert listing.funda_id == "43117443"
    assert listing.raw_status == "Verkocht"
    assert listing.asking_price is None
    assert listing.price_history == ()
    assert listing.photo_urls == ()
    assert listing.brochure_url is None


def test_normalised_listing_serialises_with_content():
    client = fx.FakePyfundaClient(fx.live_listing(), fx.live_price_history())

    listing = PyfundaListingProvider(client).fetch(fx.LIVE_URL)

    dumped = json.loads(json.dumps(dataclasses.asdict(listing)))
    assert dumped["asking_price"] == 595000
    assert dumped["price_history"][0]["price"] == 595000


def test_provider_never_searches_and_fetches_by_url_id():
    client = fx.FakePyfundaClient(fx.live_listing(), fx.live_price_history())

    PyfundaListingProvider(client).fetch(fx.LIVE_URL)

    assert client.listing_calls == ["80907644"]


def test_non_funda_url_is_invalid():
    with pytest.raises(InvalidListingUrl):
        PyfundaListingProvider(fx.FakePyfundaClient()).fetch("https://example.com/1")


def test_missing_listing_is_removed():
    client = fx.FakePyfundaClient(listing_error=ListingNotFound("gone"))

    with pytest.raises(ListingRemoved):
        PyfundaListingProvider(client).fetch(fx.LIVE_URL)


@pytest.mark.parametrize("error", [FundaRequestError("403"), FingerprintError("blocked")])
def test_rejected_requests_mean_provider_blocked(error):
    client = fx.FakePyfundaClient(listing_error=error)

    with pytest.raises(ProviderBlocked):
        PyfundaListingProvider(client).fetch(fx.LIVE_URL)


def test_listing_with_empty_floorplans_videos_and_360_photos_parses():
    bare = dataclasses.replace(
        fx.live_listing(),
        media=Media(floorplans=(), videos=(), photos_360=(), virtual_tours=()),
    )
    client = fx.FakePyfundaClient(bare, fx.live_price_history())

    listing = PyfundaListingProvider(client).fetch(fx.LIVE_URL)

    assert listing.photo_urls == ()
    assert listing.brochure_url is None
    assert listing.asking_price == 595000
