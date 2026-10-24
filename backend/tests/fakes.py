"""Test doubles for the three outside-world ports. They never touch the network."""

from app.ports import Listing, SourceFact


class FakeListingProvider:
    def __init__(self) -> None:
        self.listings: dict[str, Listing] = {}
        self.calls: list[str] = []

    def fetch(self, url: str) -> Listing:
        self.calls.append(url)
        return self.listings[url]


class FakeSourceClient:
    def __init__(self, source: str, facts: list[SourceFact] | None = None) -> None:
        self.source = source
        self.facts = facts or []
        self.calls: list[Listing] = []

    def fetch(self, listing: Listing) -> list[SourceFact]:
        self.calls.append(listing)
        return self.facts


class FakeLlmClient:
    def __init__(self) -> None:
        self.observations: list[dict] = []
        self.findings: list[dict] = []
        self.verdict: dict = {"tier": "Consider", "reasoning": "", "bid_advice": {}}
        self.rate_calls: list[tuple[dict, dict]] = []

    def observe_photos(self, photo_paths: list[str]) -> list[dict]:
        return self.observations

    def extract_findings(self, document_path: str) -> list[dict]:
        return self.findings

    def rate(self, case: dict, buyer_profile: dict) -> dict:
        self.rate_calls.append((case, buyer_profile))
        return self.verdict
