"""The three outside-world ports. Everything that touches the network sits behind one."""

from dataclasses import dataclass, field
from typing import Protocol


class ListingError(Exception):
    """Base for failures to fetch a Listing."""


class InvalidListingUrl(ListingError):
    pass


class ListingRemoved(ListingError):
    pass


class ProviderBlocked(ListingError):
    pass


class SourceSkipped(Exception):
    """A Source client cannot run for this Listing (e.g. no postcode, no API key). Not a failure."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SourceFailed(Exception):
    """A Source client tried and failed. Any other exception from a client counts as failed too."""


class DownloadFailed(Exception):
    """A Document (the funda brochure) could not be downloaded."""


class LlmError(Exception):
    """The LLM client could not produce an answer (network, quota, refusal, unparseable reply)."""


@dataclass(frozen=True)
class PricePoint:
    date: str | None
    price: int | None


@dataclass(frozen=True)
class Listing:
    funda_id: str
    url: str
    raw_status: str
    provider_id: str | None = None
    address: str | None = None
    postcode: str | None = None
    house_number: str | None = None
    house_number_suffix: str | None = None
    city: str | None = None
    asking_price: int | None = None
    living_area: int | None = None
    plot_area: int | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    construction_year: int | None = None
    energy_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    heating: str | None = None
    # Kadaster `Eigendomssituatie`, verbatim (e.g. "Volle eigendom"); distinct values across
    # parcels are joined with "; ".
    ownership_situation: str | None = None
    description: str | None = None
    price_history: tuple[PricePoint, ...] = ()
    photo_urls: tuple[str, ...] = ()
    brochure_url: str | None = None


@dataclass(frozen=True)
class SourceFact:
    """One fact from a Source. The app stamps the fetch time; `as_of` is the date the value refers to."""

    name: str
    value: object
    as_of: str | None = None


class ListingProvider(Protocol):
    def fetch(self, url: str) -> Listing: ...


class SourceClient(Protocol):
    def fetch(self, listing: Listing) -> list[SourceFact]: ...


class LlmClient(Protocol):
    def observe_photos(self, photo_paths: list[str]) -> list[dict]: ...

    def extract_findings(self, document_path: str) -> list[dict]:
        """Raw Findings for the PDF at `document_path`, each with `topic`, `present`, `statement`,
        the `quote` it rests on and its 1-based `page`. The caller checks the quote is on that page.
        Raises LlmError."""
        ...

    def rate(self, case: dict, buyer_profile: dict) -> dict:
        """The Verdict model's raw answer for a Case and the reduced Buyer Profile. Raises LlmError."""
        ...


class PhotoDownloader(Protocol):
    def download(self, url: str) -> bytes:
        """One Listing photo's bytes. Any exception means that photo is unavailable."""
        ...


class DocumentDownloader(Protocol):
    def download(self, url: str) -> bytes:
        """The file at `url` (the funda brochure). Raises DownloadFailed."""
        ...


@dataclass
class Ports:
    listing_provider: ListingProvider
    source_clients: dict[str, SourceClient] = field(default_factory=dict)
    llm_client: LlmClient | None = None
    photo_downloader: PhotoDownloader | None = None
    document_downloader: DocumentDownloader | None = None
