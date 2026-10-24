from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from app import store
from app.case import build_case
from app.comparison import summarise
from app.buyer_profile import BuyerProfile, describe_errors, reduce_profile
from app.listing_url import funda_id_from_url
from app.manual_provider import ManualEntry, ManualListingProvider
from app.ports import (
    InvalidListingUrl,
    ListingError,
    ListingProvider,
    ListingRemoved,
    Ports,
    ProviderBlocked,
)
from app.rules_loader import load_flag_rules, load_rules
from app.production_ports import build_production_ports
from app.settings import Settings
from app.source_runner import run_sources

_ERROR_RESPONSES = {
    InvalidListingUrl: (400, "bad_url"),
    ListingRemoved: (404, "listing_removed"),
    ProviderBlocked: (502, "provider_blocked"),
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    settings: Settings | None = None,
    ports: Ports | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> FastAPI:
    settings = settings or Settings()
    ports = ports or build_production_ports(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.initialise(settings.database_path)
        yield

    app = FastAPI(title="Funda Griller", lifespan=lifespan)
    app.state.settings = settings
    app.state.ports = ports

    class CaptureRequest(BaseModel):
        url: str

    class ManualEntryForm(BaseModel):
        url: str
        raw_status: str = Field(min_length=1)
        address: str | None = None
        city: str | None = None
        asking_price: int | None = Field(default=None, ge=0)
        living_area: int | None = Field(default=None, ge=0)
        plot_area: int | None = Field(default=None, ge=0)
        rooms: int | None = Field(default=None, ge=0)
        bedrooms: int | None = Field(default=None, ge=0)
        construction_year: int | None = Field(default=None, ge=1000, le=2100)
        energy_label: str | None = None
        heating: str | None = None
        description: str | None = None
        photos: list[UploadFile] = []

        @field_validator("*", mode="before")
        @classmethod
        def blank_is_absent(cls, value: object) -> object:
            """An empty form field means the fact is unknown, not zero or an empty string."""
            return (value.strip() or None) if isinstance(value, str) else value

    def capture(
        funda_id: str,
        url: str,
        provider: ListingProvider = ports.listing_provider,
        entry: str = "fetched",
    ) -> dict:
        listing = replace(provider.fetch(url), funda_id=funda_id, url=url)
        status = settings.listing_status_map.get(listing.raw_status.casefold(), "unknown")
        fetched_at = clock().isoformat()
        store.add_snapshot(settings.database_path, listing, fetched_at, status, entry)
        run_sources(settings.database_path, ports.source_clients, listing, fetched_at)
        return with_comparison(store.get_listing(settings.database_path, funda_id))

    def with_comparison(listing: dict) -> dict:
        """The Listing plus its comparison-view row. The tier stays empty until a Verdict exists,
        except a deal-breaker Hard no, which the Case already decides."""
        return {**listing, "comparison": summarise(listing["snapshots"], current_case(listing))}

    def already_captured(funda_id: str) -> JSONResponse | None:
        if store.get_listing(settings.database_path, funda_id) is None:
            return None
        return JSONResponse({"code": "already_captured", "funda_id": funda_id}, status_code=409)

    @app.exception_handler(ListingError)
    def listing_error(_: Request, error: ListingError) -> JSONResponse:
        status_code, code = _ERROR_RESPONSES.get(type(error), (502, "provider_error"))
        return JSONResponse({"code": code}, status_code=status_code)

    @app.post("/api/listings", status_code=201, response_model=None)
    def capture_listing(request: CaptureRequest) -> dict | JSONResponse:
        funda_id = funda_id_from_url(request.url)
        return already_captured(funda_id) or capture(funda_id, request.url.strip())

    @app.post("/api/listings/manual", status_code=201, response_model=None)
    def enter_listing(
        form: Annotated[ManualEntryForm, Form()],
    ) -> dict | JSONResponse:
        """Fallback when the fetch provider is broken or blocked: the user types the Listing in."""
        url = form.url.strip()
        funda_id = funda_id_from_url(url)
        if duplicate := already_captured(funda_id):
            return duplicate
        if any(not (photo.content_type or "").startswith("image/") for photo in form.photos):
            return JSONResponse({"code": "not_an_image"}, status_code=422)
        photo_urls = tuple(
            f"/api/listings/{funda_id}/photos/"
            + store.save_photo(settings.media_dir, funda_id, photo.filename or "", photo.file.read())
            for photo in form.photos
        )
        facts = form.model_dump(exclude={"url", "photos"})
        entry = ManualEntry(**{**facts, "photo_urls": photo_urls})
        return capture(funda_id, url, ManualListingProvider(entry), "manual")

    @app.get("/api/listings/{funda_id}/photos/{name}", response_model=None)
    def read_photo(funda_id: str, name: str) -> FileResponse | JSONResponse:
        path = store.photo_path(settings.media_dir, funda_id, name)
        if path is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return FileResponse(path)

    @app.post("/api/listings/{funda_id}/refetch", response_model=None)
    def refetch_listing(funda_id: str) -> dict | JSONResponse:
        existing = store.get_listing(settings.database_path, funda_id)
        if existing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return capture(funda_id, existing["url"])

    @app.post("/api/listings/{funda_id}/sources/{source}/refetch", response_model=None)
    def refetch_source(funda_id: str, source: str) -> dict | JSONResponse:
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None or source not in ports.source_clients:
            return JSONResponse({"code": "not_found"}, status_code=404)
        run_sources(
            settings.database_path,
            {source: ports.source_clients[source]},
            store.listing_from_snapshot(funda_id, listing["url"], listing["snapshots"][0]),
            clock().isoformat(),
        )
        return current_case(listing)

    @app.get("/api/listings/{funda_id}/case", response_model=None)
    def read_case(funda_id: str) -> dict | JSONResponse:
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return current_case(listing)

    def current_case(listing: dict) -> dict:
        funda_id = listing["funda_id"]
        latest = store.latest_buyer_profile(settings.database_path)
        now = clock()
        return build_case(
            funda_id,
            listing["snapshots"][0],
            latest["version"] if latest else None,
            BuyerProfile.model_validate(latest["profile"]) if latest else None,
            load_rules(settings.affordability_rules_path, now.year),
            load_flag_rules(settings.flag_rules_path),
            now,
            list(ports.source_clients),
            store.source_runs(settings.database_path, funda_id),
            settings.source_ttl_days,
        )

    @app.get("/api/listings")
    def list_listings(include_archived: bool = False) -> list[dict]:
        """Archived Listings are hidden unless asked for. Sorting and filtering happen in the view."""
        return [
            with_comparison(listing)
            for listing in store.list_listings(settings.database_path)
            if include_archived or not listing["archived"]
        ]

    def set_archived(funda_id: str, archived: bool) -> dict | JSONResponse:
        if store.get_listing(settings.database_path, funda_id) is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        store.set_archived(settings.database_path, funda_id, archived, clock().isoformat())
        return with_comparison(store.get_listing(settings.database_path, funda_id))

    @app.post("/api/listings/{funda_id}/archive", response_model=None)
    def archive_listing(funda_id: str) -> dict | JSONResponse:
        return set_archived(funda_id, True)

    @app.post("/api/listings/{funda_id}/restore", response_model=None)
    def restore_listing(funda_id: str) -> dict | JSONResponse:
        return set_archived(funda_id, False)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"errors": describe_errors(list(error.errors()))}
        )

    @app.put("/api/buyer-profile")
    def save_buyer_profile(profile: BuyerProfile) -> dict:
        return store.save_buyer_profile(settings.database_path, profile.model_dump(mode="json"))

    def latest_or_404() -> dict:
        latest = store.latest_buyer_profile(settings.database_path)
        if latest is None:
            raise HTTPException(status_code=404, detail="Nog geen koperprofiel")
        return latest

    @app.get("/api/buyer-profile")
    def read_buyer_profile() -> dict:
        return latest_or_404()

    @app.get("/api/buyer-profile/versions")
    def list_buyer_profile_versions() -> list[dict]:
        return store.buyer_profile_versions(settings.database_path)

    @app.get("/api/buyer-profile/reduced")
    def read_reduced_buyer_profile() -> dict:
        latest = latest_or_404()
        return reduce_profile(latest["version"], BuyerProfile.model_validate(latest["profile"]))

    return app

