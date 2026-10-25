"""pyfunda objects shaped like the two prototype listings (live and sold). Hand-built, no network."""

from funda.listing import (
    Address,
    Areas,
    Characteristic,
    CharacteristicSection,
    GeoLocation,
    Listing,
    Media,
    MediaItem,
    PriceChange,
    PriceHistory,
    PropertyDetails,
    Rooms,
    Price,
    Urls,
)

LIVE_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/"
SOLD_URL = "https://www.funda.nl/detail/koop/verkocht/amsterdam/appartement-keizersgracht-1/43117443"


def live_listing() -> Listing:
    return Listing(
        listing_id="17270371",
        global_id=80907644,
        tiny_id="17270371",
        price=Price(amount=595000),
        address=Address(
            title="Buchterweg 15",
            city="Holtum",
            house_number="15",
            house_number_suffix="a",
            postcode="6118 AB",
        ),
        areas=Areas(living=152, plot=410),
        rooms=Rooms(total=6, bedrooms=4),
        property_details=PropertyDetails(
            construction_year=1931,
            energy_label="B",
            status="available",
            raw_status="Beschikbaar",
        ),
        location=GeoLocation(latitude=51.0, longitude=5.8),
        urls=Urls(full=LIVE_URL),
        media=Media(
            photos=(
                MediaItem(id="1", url="https://cloud.funda.nl/p1.jpg"),
                MediaItem(id="2", url="https://cloud.funda.nl/p2.jpg"),
            ),
            brochure_url="https://cloud.funda.nl/brochure.pdf",
        ),
        description="Vrijstaande woning met garage.",
        characteristics=(
            CharacteristicSection(
                title="Energie",
                items=(Characteristic(label="Verwarming", value="Warmtepomp"),),
            ),
            kadaster("Volle eigendom"),
        ),
    )


def kadaster(*ownership: str) -> CharacteristicSection:
    """The `Kadastrale gegevens` section as seen on the prototype listings: one parcel item per
    parcel, with the ownership situation as a child item."""
    return CharacteristicSection(
        title="Kadastrale gegevens",
        items=tuple(
            Characteristic(
                id="cadastral-parcel",
                label=f"HOLTUM A {100 + n}",
                children=(
                    Characteristic(id="cadastral-area", label="Oppervlakte", value="410 m²"),
                    Characteristic(id="cadastral-ownershipsituation", label="Eigendomssituatie", value=value),
                ),
            )
            for n, value in enumerate(ownership)
        ),
    )


def live_price_history() -> PriceHistory:
    return PriceHistory(
        status="ok",
        changes=(
            PriceChange(price=595000, status="asking_price", date="2026-10-21"),
            PriceChange(price=392000, status="woz", date="2025-01-01"),
        ),
    )


def sold_listing() -> Listing:
    """Sold listing: bare attributes, no price/areas objects filled, raw status only in characteristics."""
    return Listing(
        global_id=43117443,
        urls=Urls(full=SOLD_URL),
        property_details=PropertyDetails(status="sold"),
        characteristics=(
            CharacteristicSection(
                title="Overdracht",
                items=(Characteristic(label="Status", value="Verkocht"),),
            ),
        ),
    )


class FakePyfundaClient:
    """Stands in for funda.Funda. `search` is a trap: the provider must never call it."""

    def __init__(self, listing=None, history=None, listing_error=None, history_error=None):
        self._listing = listing
        self._history = history
        self._listing_error = listing_error
        self._history_error = history_error
        self.listing_calls: list[str] = []

    def listing(self, listing_id):
        self.listing_calls.append(listing_id)
        if self._listing_error:
            raise self._listing_error
        return self._listing

    def price_history(self, listing):
        if self._history_error:
            raise self._history_error
        return self._history

    def search(self, *_args, **_kwargs):
        raise AssertionError("search() must never be called")
