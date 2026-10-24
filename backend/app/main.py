from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, date, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import store
from app.case import build_case
from app.buyer_profile import BuyerProfile, describe_errors, reduce_profile
from app.listing_url import funda_id_from_url
from app.ports import (
    InvalidListingUrl,
    ListingError,
    ListingRemoved,
    Ports,
    ProviderBlocked,
)
from app.rules_loader import load_flag_rules, load_rules
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
            replace(listing, funda_id=funda_id, url=url),
            datetime.now(UTC).isoformat(),
            status,
        )
        return store.get_listing(settings.database_path, funda_id)

    @app.exception_handler(ListingError)
    def listing_error(_: Request, error: ListingError) -> JSONResponse:
        status_code, code = _ERROR_RESPONSES.get(type(error), (502, "provider_error"))
        return JSONResponse({"code": code}, status_code=status_code)

    @app.post("/api/listings", status_code=201, response_model=None)
    def capture_listing(request: CaptureRequest) -> dict | JSONResponse:
        funda_id = funda_id_from_url(request.url)
        if store.get_listing(settings.database_path, funda_id) is not None:
            return JSONResponse(
                {"code": "already_captured", "funda_id": funda_id}, status_code=409
            )
        return capture(funda_id, request.url.strip())

    @app.post("/api/listings/{funda_id}/refetch", response_model=None)
    def refetch_listing(funda_id: str) -> dict | JSONResponse:
        existing = store.get_listing(settings.database_path, funda_id)
        if existing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return capture(funda_id, existing["url"])

    @app.get("/api/listings/{funda_id}/case", response_model=None)
    def read_case(funda_id: str) -> dict | JSONResponse:
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        latest = store.latest_buyer_profile(settings.database_path)
        today = date.today()
        return build_case(
            funda_id,
            listing["snapshots"][0],
            latest["version"] if latest else None,
            BuyerProfile.model_validate(latest["profile"]) if latest else None,
            load_rules(settings.affordability_rules_path, today.year),
            load_flag_rules(settings.flag_rules_path),
            today,
        )

    @app.get("/api/listings")
    def list_listings() -> list[dict]:
        return store.list_listings(settings.database_path)

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

