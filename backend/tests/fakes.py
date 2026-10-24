"""Test doubles for the three outside-world ports, plus a controllable clock. They never touch the network."""

from collections.abc import Callable
from datetime import datetime, timedelta

from app.ports import Listing, SourceFact


class FakeListingProvider:
    def __init__(self) -> None:
        self.listings: dict[str, Listing | Exception] = {}
        self.calls: list[str] = []

    def fetch(self, url: str) -> Listing:
        self.calls.append(url)
        result = self.listings[url]
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
        self.observations: list[dict] = []
        self.findings: list[dict] = []
        self.verdict: dict | Callable[[dict, dict], dict] | Exception = {
            "tier": "skip",
            "summary": "",
            "reasoning": "Geen bijzonderheden.",
            "cited_flags": [],
            "bid_advice": None,
        }
        self.rate_calls: list[tuple[dict, dict]] = []

    def observe_photos(self, photo_paths: list[str]) -> list[dict]:
        return self.observations

    def extract_findings(self, document_path: str) -> list[dict]:
        return self.findings

    def rate(self, case: dict, buyer_profile: dict) -> dict:
        self.rate_calls.append((case, buyer_profile))
        if isinstance(self.verdict, Exception):
            raise self.verdict
        return self.verdict(case, buyer_profile) if callable(self.verdict) else self.verdict
