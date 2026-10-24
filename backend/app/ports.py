"""The three outside-world ports. Everything that touches the network sits behind one."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Listing:
    funda_id: str
    url: str
    raw_status: str


@dataclass(frozen=True)
class SourceFact:
    source: str
    name: str
    value: object
    fetched_at: str


class ListingProvider(Protocol):
    def fetch(self, url: str) -> Listing: ...


class SourceClient(Protocol):
    def fetch(self, listing: Listing) -> list[SourceFact]: ...


class LlmClient(Protocol):
    def observe_photos(self, photo_paths: list[str]) -> list[dict]: ...

    def extract_findings(self, document_path: str) -> list[dict]: ...

    def rate(self, case: dict, buyer_profile: dict) -> dict: ...


@dataclass
class Ports:
    listing_provider: ListingProvider
    source_clients: dict[str, SourceClient] = field(default_factory=dict)
    llm_client: LlmClient | None = None
