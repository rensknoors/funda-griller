"""Listing provider adapter over pyfunda. Fetches one Listing by URL; never searches."""

from typing import Any

from funda.exceptions import (
    FingerprintError,
    FundaRequestError,
    ListingNotFound,
    PriceHistoryError,
)

from app.listing_url import funda_id_from_url
from app.ports import Listing, ListingRemoved, PricePoint, ProviderBlocked


def _get(obj: Any, *path: str) -> Any:
    """Walk attributes, returning None as soon as one is missing."""
    for name in path:
        if obj is None:
            return None
        obj = getattr(obj, name, None)
    return obj


def _text(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


class PyfundaListingProvider:
    def __init__(self, client: Any) -> None:
        self._client = client

    def fetch(self, url: str) -> Listing:
        funda_id = funda_id_from_url(url)
        try:
            found = self._client.listing(funda_id)
        except ListingNotFound as error:
            raise ListingRemoved(url) from error
        except (FundaRequestError, FingerprintError) as error:
            raise ProviderBlocked(url) from error
        return Listing(
            funda_id=funda_id,
            url=url,
            raw_status=self._raw_status(found),
            provider_id=_text(_get(found, "tiny_id") or _get(found, "listing_id")),
            address=_get(found, "address", "title"),
            postcode=_text(_get(found, "address", "postcode")),
            house_number=_text(_get(found, "address", "house_number")),
            house_number_suffix=_text(_get(found, "address", "house_number_suffix")),
            city=_get(found, "address", "city"),
            asking_price=_get(found, "price", "amount"),
            living_area=_get(found, "areas", "living"),
            plot_area=_get(found, "areas", "plot"),
            rooms=_get(found, "rooms", "total"),
            bedrooms=_get(found, "rooms", "bedrooms"),
            construction_year=_get(found, "property_details", "construction_year"),
            energy_label=_get(found, "property_details", "energy_label"),
            latitude=_get(found, "location", "latitude"),
            longitude=_get(found, "location", "longitude"),
            heating=_text(self._characteristic(found, "Verwarming")),
            ownership_situation=self._ownership_situation(found),
            description=_get(found, "description"),
            price_history=self._price_history(found),
            photo_urls=tuple(_get(found, "media", "photo_urls") or ()),
            brochure_url=_get(found, "media", "brochure_url"),
        )

    def _raw_status(self, found: Any) -> str:
        return (
            _text(_get(found, "property_details", "raw_status"))
            or _text(self._characteristic(found, "Status"))
            or _text(_get(found, "property_details", "status"))
            or ""
        )

    @staticmethod
    def _characteristic(found: Any, label: str) -> Any:
        lookup = getattr(found, "characteristic", None)
        return lookup(label) if callable(lookup) else None

    @staticmethod
    def _ownership_situation(found: Any) -> str | None:
        """The Kadaster `Eigendomssituatie` of every parcel (item id `cadastral-ownershipsituation`,
        found in ticket 02), verbatim; distinct values joined so no parcel's erfpacht is hidden."""
        values: list[str] = []
        for section in _get(found, "characteristics") or ():
            for root in getattr(section, "items", ()):
                for item in root.walk():
                    is_ownership = item.id == "cadastral-ownershipsituation" or (
                        item.id is None and (item.label or "").casefold() == "eigendomssituatie"
                    )
                    value = _text(item.value) if is_ownership else None
                    if value and value not in values:
                        values.append(value)
        return "; ".join(values) or None

    def _price_history(self, found: Any) -> tuple[PricePoint, ...]:
        try:
            history = self._client.price_history(found)
        except PriceHistoryError:
            return ()
        return tuple(
            PricePoint(date=change.date, price=change.price)
            for change in _get(history, "changes") or ()
            if change.status == "asking_price"
        )
