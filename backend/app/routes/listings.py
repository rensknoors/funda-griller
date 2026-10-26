"""Listings: capture by URL or by hand, photos, refetch, Sources, Case, Observations, archive."""

from typing import Annotated

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from app import store
from app.listing_url import funda_id_from_url
from app.manual_provider import ManualEntry, ManualListingProvider
from app.source_runner import run_sources
from app.wiring import NotFound, Wiring


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
    ownership_situation: str | None = None
    description: str | None = None
    photos: list[UploadFile] = []

    @field_validator("*", mode="before")
    @classmethod
    def blank_is_absent(cls, value: object) -> object:
        """An empty form field means the fact is unknown, not zero or an empty string."""
        return (value.strip() or None) if isinstance(value, str) else value


def routes(w: Wiring) -> APIRouter:
    router = APIRouter(prefix="/api/listings")
    settings = w.settings

    def already_captured(funda_id: str) -> JSONResponse | None:
        if store.get_listing(settings.database_path, funda_id) is None:
            return None
        return JSONResponse({"code": "already_captured", "funda_id": funda_id}, status_code=409)

    @router.post("", status_code=201, response_model=None)
    def capture_listing(request: CaptureRequest) -> dict | JSONResponse:
        funda_id = funda_id_from_url(request.url)
        return already_captured(funda_id) or w.capture(funda_id, request.url.strip())

    @router.post("/manual", status_code=201, response_model=None)
    def enter_listing(form: Annotated[ManualEntryForm, Form()]) -> dict | JSONResponse:
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
        return w.capture(funda_id, url, ManualListingProvider(entry), "manual")

    @router.get("", response_model=None)
    def list_listings(include_archived: bool = False) -> list[dict]:
        """Archived Listings are hidden unless asked for. Sorting and filtering happen in the view."""
        return [
            w.with_comparison(listing)
            for listing in store.list_listings(settings.database_path)
            if include_archived or not listing["archived"]
        ]

    @router.get("/{funda_id}/photos/{name}", response_model=None)
    def read_photo(funda_id: str, name: str) -> FileResponse:
        path = store.photo_path(settings.media_dir, funda_id, name)
        if path is None:
            raise NotFound()
        return FileResponse(path)

    @router.post("/{funda_id}/refetch", response_model=None)
    def refetch_listing(funda_id: str) -> dict:
        return w.capture(funda_id, w.listing(funda_id)["url"])

    @router.post("/{funda_id}/sources/{source}/refetch", response_model=None)
    def refetch_source(funda_id: str, source: str) -> dict:
        listing = w.listing(funda_id)
        if source not in w.source_names():
            raise NotFound()
        run_sources(
            settings.database_path,
            {source: w.source_clients()[source]},
            store.listing_from_snapshot(funda_id, listing["url"], listing["snapshots"][0]),
            w.clock().isoformat(),
        )
        return w.current_case(listing)

    @router.get("/{funda_id}/case", response_model=None)
    def read_case(funda_id: str) -> dict:
        return w.current_case(w.listing(funda_id))

    @router.post("/{funda_id}/observations", response_model=None)
    def rerun_observations(funda_id: str) -> dict | JSONResponse:
        """Re-run the vision model over the latest snapshot's photos, e.g. after a model change."""
        listing = w.listing(funda_id)
        photos = listing["snapshots"][0].get("photos", [])
        if not photos:
            return JSONResponse({"code": "no_photos"}, status_code=409)
        if w.ports.llm_client is None:
            return JSONResponse({"code": "llm_unavailable"}, status_code=503)
        if w.observe(funda_id, photos, w.clock().isoformat(), rerun=True) == "failed":
            return JSONResponse({"code": "llm_unavailable"}, status_code=502)
        return w.current_case(listing)

    def set_archived(funda_id: str, archived: bool) -> dict:
        w.listing(funda_id)
        store.set_archived(settings.database_path, funda_id, archived, w.clock().isoformat())
        return w.with_comparison(w.listing(funda_id))

    @router.post("/{funda_id}/archive", response_model=None)
    def archive_listing(funda_id: str) -> dict:
        return set_archived(funda_id, True)

    @router.post("/{funda_id}/restore", response_model=None)
    def restore_listing(funda_id: str) -> dict:
        return set_archived(funda_id, False)

    return router
