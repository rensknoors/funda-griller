"""The commute Source: travel time from the Listing to each Buyer Profile commute destination.

The destination address is geocoded once and cached locally; only coordinates reach the router.
Car and bike are both computed and the faster one counts; public transport is not included.
"""

from pathlib import Path

from app import store
from app.buyer_profile import CommuteDestination
from app.ports import Coordinates, Geocoder, Listing, SourceFact, SourceFailed, SourceSkipped, TravelTimeRouter

MODES = ("car", "bike")


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
        located = [
            (destination.label, place)
            for destination in self._destinations
            if (place := self._locate(destination.address)) is not None
        ]
        if not located:
            raise SourceFailed("destination_not_found")
        origin = (listing.latitude, listing.longitude)
        places = [place for _, place in located]
        by_mode = {mode: self._router.travel_minutes(origin, places, mode) for mode in MODES}
        facts = []
        for index, (label, _) in enumerate(located):
            minutes = {mode: round(by_mode[mode][index]) for mode in MODES if by_mode[mode][index] is not None}
            if not minutes:
                continue
            fastest = min(minutes, key=lambda mode: minutes[mode])
            facts.append(
                SourceFact(
                    name="travel_minutes",
                    value={
                        "destination": label,
                        "minutes": minutes[fastest],
                        "mode": fastest,
                        "minutes_by_mode": minutes,
                        "public_transport": False,
                    },
                )
            )
        if not facts:
            raise SourceFailed("no_route")
        return facts

    def _locate(self, address: str) -> Coordinates | None:
        cached = store.cached_geocode(self._database_path, address)
        if cached is not None:
            return cached
        place = self._geocoder.geocode(address)
        if place is not None:
            store.cache_geocode(self._database_path, address, place)
        return place
