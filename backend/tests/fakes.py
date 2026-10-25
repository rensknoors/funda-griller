"""Test doubles for the outside-world ports, plus a controllable clock. They never touch the network."""

from collections.abc import Callable
from datetime import datetime, timedelta

from app.ports import CommuteMode, Coordinates, DownloadFailed, Listing, SourceFact


class FakeListingProvider:
    """`listings` maps a URL to its Listing or error, or to a list of them returned one per fetch
    (the last one repeats), for a Listing whose status changes between fetches."""

    def __init__(self) -> None:
        self.listings: dict[str, Listing | Exception | list[Listing | Exception]] = {}
        self.calls: list[str] = []

    def fetch(self, url: str) -> Listing:
        self.calls.append(url)
        result = self.listings[url]
        if isinstance(result, list):
            result = result.pop(0) if len(result) > 1 else result[0]
        if isinstance(result, Exception):
            raise result
        return result


class FakeSourceClient:
    """Returns `facts`, or raises `error` (a failure or a SourceSkipped) when set."""

    def __init__(self, source: str, facts: list[SourceFact] | None = None) -> None:
        self.source = source
        self.facts = facts or []
        self.error: Exception | None = None
        self.calls: list[Listing] = []

    def fetch(self, listing: Listing) -> list[SourceFact]:
        self.calls.append(listing)
        if self.error is not None:
            raise self.error
        return self.facts


class FakePhotoDownloader:
    """`photos` maps a photo URL to its bytes or an exception to raise; an unlisted URL returns
    bytes derived from it. Every download is recorded."""

    def __init__(self) -> None:
        self.photos: dict[str, bytes | Exception] = {}
        self.calls: list[str] = []

    def download(self, url: str) -> bytes:
        self.calls.append(url)
        result = self.photos.get(url, b"photo:" + url.encode())
        if isinstance(result, Exception):
            raise result
        return result


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, days: int) -> None:
        self.now += timedelta(days=days)


class FakeLlmClient:
    """`verdict` is the canned answer to `rate`: a dict, a function of (case, buyer_profile), or an
    exception to raise. Every `rate` call is recorded."""

    def __init__(self) -> None:
        self.observations: list[dict] | Exception = []
        # Canned Findings: a list, a function of the Document's path, or an exception to raise.
        self.findings: list[dict] | Callable[[str], list[dict]] | Exception = []
        self.extract_calls: list[str] = []
        self.verdict: dict | Callable[[dict, dict], dict] | Exception = {
            "tier": "skip",
            "summary": "",
            "reasoning": "Geen bijzonderheden.",
            "cited_flags": [],
            "bid_advice": None,
        }
        self.rate_calls: list[tuple[dict, dict]] = []
        self.observe_calls: list[list[str]] = []

    def observe_photos(self, photo_paths: list[str]) -> list[dict]:
        """Returns `observations` (canned raw answers) or raises it when it is an exception."""
        self.observe_calls.append(list(photo_paths))
        if isinstance(self.observations, Exception):
            raise self.observations
        return self.observations

    def extract_findings(self, document_path: str) -> list[dict]:
        self.extract_calls.append(document_path)
        if isinstance(self.findings, Exception):
            raise self.findings
        return self.findings(document_path) if callable(self.findings) else self.findings

    def rate(self, case: dict, buyer_profile: dict) -> dict:
        self.rate_calls.append((case, buyer_profile))
        if isinstance(self.verdict, Exception):
            raise self.verdict
        return self.verdict(case, buyer_profile) if callable(self.verdict) else self.verdict


class FakeDocumentDownloader:
    """`documents` maps a URL to its bytes or an exception; any other URL returns `default`."""

    def __init__(self, default: bytes) -> None:
        self.default = default
        self.documents: dict[str, bytes | Exception] = {}
        self.calls: list[str] = []

    def download(self, url: str) -> bytes:
        self.calls.append(url)
        result = self.documents.get(url, self.default)
        if isinstance(result, Exception):
            raise result
        return result


class FakeGeocoder:
    """`places` maps an address to its (latitude, longitude); an unlisted address is not found.
    `error` is raised when set. Every lookup is recorded."""

    def __init__(self) -> None:
        self.places: dict[str, Coordinates] = {}
        self.error: Exception | None = None
        self.calls: list[str] = []

    def geocode(self, address: str) -> Coordinates | None:
        self.calls.append(address)
        if self.error is not None:
            raise self.error
        return self.places.get(address)


class FakeTravelTimeRouter:
    """`minutes` maps (mode, destination) to the travel minutes from any origin; an unlisted pair
    is unroutable. `error` is raised by a request when set, `unavailable` by the availability
    check (e.g. SourceSkipped("no_api_key")). Every request is recorded."""

    def __init__(self) -> None:
        self.minutes: dict[tuple[CommuteMode, Coordinates], float] = {}
        self.error: Exception | None = None
        self.unavailable: Exception | None = None
        self.calls: list[tuple[Coordinates, list[Coordinates], CommuteMode]] = []

    def check_available(self) -> None:
        if self.unavailable is not None:
            raise self.unavailable

    def travel_minutes(
        self, origin: Coordinates, destinations: list[Coordinates], mode: CommuteMode
    ) -> list[float | None]:
        self.check_available()
        self.calls.append((origin, list(destinations), mode))
        if self.error is not None:
            raise self.error
        return [self.minutes.get((mode, destination)) for destination in destinations]
