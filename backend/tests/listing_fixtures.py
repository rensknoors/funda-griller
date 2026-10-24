"""Normalised Listings shaped like the two prototype listings (one live, one sold)."""

from app.ports import Listing, PricePoint

LIVE_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/"
SOLD_URL = "https://www.funda.nl/detail/koop/verkocht/amsterdam/appartement-keizersgracht-1/43117443/"


def live_listing(**overrides) -> Listing:
    fields = dict(
        funda_id="80907644",
        provider_id="17270371",
        url=LIVE_URL,
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
        latitude=51.0,
        longitude=5.8,
        heating="Warmtepomp",
        description="Vrijstaande woning met garage.",
        price_history=(PricePoint(date="2026-10-21", price=595000),),
        photo_urls=("https://cloud.funda.nl/p1.jpg", "https://cloud.funda.nl/p2.jpg"),
        brochure_url="https://cloud.funda.nl/brochure.pdf",
    )
    return Listing(**{**fields, **overrides})


def sold_listing(**overrides) -> Listing:
    """Sold listing: most optional facts absent."""
    fields = dict(
        funda_id="43117443",
        provider_id="9988776",
        url=SOLD_URL,
        raw_status="Verkocht",
        asking_price=450000,
        living_area=88,
    )
    return Listing(**{**fields, **overrides})
