"""What the HTTP routers share: configuration, ports, the clock, and the steps several routes take
(capture a Listing, build its current Case, add its comparison row, discard a Document)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from app import documents, store
from app.assembly import assemble_case
from app.buyer_profile import BuyerProfile
from app.case import VersionedProfile
from app.comparison import summarise
from app.observations import observe
from app.photos import keep_photos, photo_set
from app.ports import ListingProvider, Ports
from app.settings import Settings
from app.source_runner import run_sources

# Sources fetched only when the user asks for them, never on capture or a Listing refetch:
# comparables cost one provider fetch per comparable.
ON_REQUEST_SOURCES = frozenset({"comparables"})


class NotFound(Exception):
    """Answered as 404 with `{"code": code}`, the shape every API error has."""

    def __init__(self, code: str = "not_found") -> None:
        super().__init__(code)
        self.code = code


@dataclass
class Wiring:
    settings: Settings
    ports: Ports
    clock: Callable[[], datetime]

    def listing(self, funda_id: str) -> dict:
        listing = store.get_listing(self.settings.database_path, funda_id)
        if listing is None:
            raise NotFound()
        return listing

    def buyer_profile(self) -> dict:
        latest = store.latest_buyer_profile(self.settings.database_path)
        if latest is None:
            raise NotFound("no_buyer_profile")
        return latest

    def document(self, funda_id: str, document_id: int) -> dict:
        document = store.get_document(self.settings.database_path, funda_id, document_id)
        if document is None:
            raise NotFound()
        return document

    def capture(self, funda_id: str, url: str, provider: ListingProvider | None = None, entry: str = "fetched") -> dict:
        settings, ports = self.settings, self.ports
        listing = replace((provider or ports.listing_provider).fetch(url), funda_id=funda_id, url=url)
        status = settings.listing_status_map.get(listing.raw_status.casefold(), "unknown")
        fetched_at = self.clock().isoformat()
        existing = store.get_listing(settings.database_path, funda_id)
        photos = keep_photos(
            settings.media_dir,
            ports.photo_downloader,
            funda_id,
            listing.photo_urls,
            existing["snapshots"][0].get("photos", []) if existing else [],
        )
        store.add_snapshot(settings.database_path, listing, fetched_at, status, entry, photos)
        automatic = {n: c for n, c in ports.source_clients.items() if n not in ON_REQUEST_SOURCES}
        run_sources(settings.database_path, automatic, listing, fetched_at)
        self.observe(funda_id, photos, fetched_at)
        self._attach_brochure(funda_id, listing.brochure_url, fetched_at)
        return self.with_comparison(store.get_listing(settings.database_path, funda_id))

    def observe(self, funda_id: str, photos: list[dict], at: str, rerun: bool = False) -> str | None:
        settings = self.settings
        return observe(
            settings.database_path, settings.media_dir, self.ports.llm_client, settings.vision_model,
            funda_id, photos, at, rerun,
        )

    def _attach_brochure(self, funda_id: str, url: str | None, now: str) -> None:
        """Download the funda brochure as a Document, once per brochure URL. A new URL replaces the
        old brochure and its Findings."""
        settings = self.settings
        if not url or self.ports.document_downloader is None:
            return
        brochures = [d for d in store.documents(settings.database_path, funda_id) if d["kind"] == "brochure"]
        if any(d["source_url"] == url for d in brochures):
            return
        for old in brochures:
            self.discard_document(funda_id, old)
        document_id = store.add_document(settings.database_path, funda_id, "brochure", "Brochure (funda)", now)
        store.update_document(settings.database_path, document_id, source_url=url)
        documents.download_and_analyse(
            settings.database_path, settings.media_dir, funda_id,
            store.get_document(settings.database_path, funda_id, document_id),
            self.ports.document_downloader, self.ports.llm_client, settings.vision_model, now,
        )

    def discard_document(self, funda_id: str, document: dict) -> None:
        """Remove a Document's file and row; its Findings leave the Case with it."""
        store.delete_document_file(self.settings.media_dir, funda_id, document["stored_name"])
        store.delete_document(self.settings.database_path, document["id"])

    def current_case(self, listing: dict) -> dict:
        settings, funda_id = self.settings, listing["funda_id"]
        latest = store.latest_buyer_profile(settings.database_path)
        snapshot = listing["snapshots"][0]
        identity = photo_set(snapshot.get("photos", []))
        return assemble_case(
            settings,
            funda_id,
            snapshot,
            VersionedProfile(latest["version"], BuyerProfile.model_validate(latest["profile"])) if latest else None,
            self.clock(),
            list(self.ports.source_clients),
            store.source_runs(settings.database_path, funda_id),
            store.observation_runs(settings.database_path, funda_id, identity) if identity else None,
            store.documents(settings.database_path, funda_id),
        )

    def with_comparison(self, listing: dict) -> dict:
        """The Listing plus its comparison-view row: the latest Verdict's tier, or none until a
        Verdict exists. A deal-breaker Hard no in the Case overrides it."""
        verdicts = store.verdicts(self.settings.database_path, listing["funda_id"])
        tier = verdicts[0]["tier"] if verdicts else None
        return {**listing, "comparison": summarise(listing["snapshots"], self.current_case(listing), tier)}
