"""Listing provider adapter over a manual entry: the fallback when the fetch provider is broken or blocked."""

from dataclasses import dataclass

from app.listing_url import funda_id_from_url
from app.ports import Listing


@dataclass(frozen=True)
class ManualEntry:
    """Core Listing facts as typed in by the user; photo_urls point at photos they uploaded."""

    raw_status: str
    address: str | None = None
    city: str | None = None
    asking_price: int | None = None
    living_area: int | None = None
    plot_area: int | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    construction_year: int | None = None
    energy_label: str | None = None
    heating: str | None = None
    description: str | None = None
    photo_urls: tuple[str, ...] = ()


class ManualListingProvider:
    def __init__(self, entry: ManualEntry) -> None:
        self._entry = entry

    def fetch(self, url: str) -> Listing:
        entry = self._entry
        return Listing(
            funda_id=funda_id_from_url(url),
            url=url,
            raw_status=entry.raw_status,
            address=entry.address,
            city=entry.city,
            asking_price=entry.asking_price,
            living_area=entry.living_area,
            plot_area=entry.plot_area,
            rooms=entry.rooms,
            bedrooms=entry.bedrooms,
            construction_year=entry.construction_year,
            energy_label=entry.energy_label,
            heating=entry.heating,
            description=entry.description,
            photo_urls=entry.photo_urls,
        )
