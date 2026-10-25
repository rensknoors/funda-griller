"""The commute Source: travel time from the Listing to each Buyer Profile commute destination.

The destination address is geocoded once and cached locally; only coordinates reach the router.
Car and bike are both computed and the faster one counts; public transport is not included.
"""

from pathlib import Path

from app import store
from app.buyer_profile import CommuteDestination
from app.ports import CommuteMode, Coordinates, Geocoder, Listing, SourceFact, SourceFailed, SourceSkipped, TravelTimeRouter

MODES: tuple[CommuteMode, ...] = ("car", "bike")


class CommuteSource:
    def __init__(
        self,
        database_path: Path,
        geocoder: Geocoder,
        router: TravelTimeRouter,
        destinations: list[CommuteDestination],
    ) -> None:
        self._database_path = database_path
        self._geocoder = geocoder
        self._router = router
        self._destinations = destinations

    def fetch(self, listing: Listing) -> list[SourceFact]:
        if listing.latitude is None or listing.longitude is None:
            raise SourceSkipped("no_coordinates")
        if not self._destinations:
            raise SourceSkipped("no_destinations")
        # Before geocoding: a Source that will be skipped sends no address anywhere.
        self._router.check_available()
        places = {destination.label: self._locate(destination.address) for destination in self._destinations}
        if all(place is None for place in places.values()):
            raise SourceFailed("destination_not_found")
        origin = (listing.latitude, listing.longitude)
        found = [(label, place) for label, place in places.items() if place is not None]
        by_mode = {mode: self._router.travel_minutes(origin, [place for _, place in found], mode) for mode in MODES}
        minutes = {
            label: {mode: round(by_mode[mode][index]) for mode in MODES if by_mode[mode][index] is not None}
            for index, (label, _) in enumerate(found)
        }
        if not any(minutes.values()):
            raise SourceFailed("no_route")
        # One fact per destination, so one that was not found or not routable is shown, not dropped.
        return [_travel_fact(label, minutes.get(label), places[label]) for label in places]

    def _locate(self, address: str) -> Coordinates | None:
        cached = store.cached_geocode(self._database_path, address)
        if cached is not None:
            return cached
        place = self._geocoder.geocode(address)
        if place is not None:
            store.cache_geocode(self._database_path, address, place)
        return place


def _travel_fact(label: str, minutes: dict[CommuteMode, int] | None, place: Coordinates | None) -> SourceFact:
    if place is None or not minutes:
        unavailable = "destination_not_found" if place is None else "no_route"
        return SourceFact(name="travel_minutes", value={"destination": label, "minutes": None, "unavailable": unavailable})
    fastest = min(minutes, key=lambda mode: minutes[mode])
    return SourceFact(
        name="travel_minutes",
        value={
            "destination": label,
            "minutes": minutes[fastest],
            "mode": fastest,
            "minutes_by_mode": minutes,
            "public_transport": False,
        },
    )
