from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import store
from app.listing_url import funda_id_from_url
from app.ports import (
    InvalidListingUrl,
    ListingError,
    ListingRemoved,
    Ports,
    ProviderBlocked,
)
from app.production_ports import build_production_ports
from app.settings import Settings

_ERROR_RESPONSES = {
    InvalidListingUrl: (400, "bad_url"),
    ListingRemoved: (404, "listing_removed"),
    ProviderBlocked: (502, "provider_blocked"),
}


def create_app(settings: Settings | None = None, ports: Ports | None = None) -> FastAPI:
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

    def capture(funda_id: str, url: str) -> dict:
        listing = ports.listing_provider.fetch(url)
        status = settings.listing_status_map.get(listing.raw_status.casefold(), "unknown")
        store.add_snapshot(
            settings.database_path,
            funda_id,
            url,
            listing,
            datetime.now(UTC).isoformat(),
            status,
        )
        return store.get_listing(settings.database_path, funda_id)

    @app.exception_handler(ListingError)
    def listing_error(_: Request, error: ListingError) -> JSONResponse:
        status_code, code = _ERROR_RESPONSES[type(error)]
        return JSONResponse({"code": code}, status_code=status_code)

    @app.post("/api/listings", status_code=201)
    def capture_listing(request: CaptureRequest) -> dict:
        funda_id = funda_id_from_url(request.url)
        if store.get_listing(settings.database_path, funda_id) is not None:
            return JSONResponse(
                {"code": "already_captured", "funda_id": funda_id}, status_code=409
            )
        return capture(funda_id, request.url.strip())

    @app.post("/api/listings/{funda_id}/refetch")
    def refetch_listing(funda_id: str) -> dict:
        existing = store.get_listing(settings.database_path, funda_id)
        if existing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return capture(funda_id, existing["url"])

    @app.get("/api/listings")
    def list_listings() -> list[dict]:
        return store.list_listings(settings.database_path)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

