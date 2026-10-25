"""The FastAPI app: wiring, the routers per resource, and one error shape (`{"code": ...}`)."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import store
from app.buyer_profile import describe_errors
from app.ports import InvalidListingUrl, ListingError, ListingRemoved, Ports, ProviderBlocked
from app.production_ports import build_production_ports
from app.routes import buyer_profile, documents, listings, verdicts
from app.settings import Settings
from app.wiring import NotFound, Wiring

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
    wiring = Wiring(settings, ports, clock)
    for resource in (listings, documents, verdicts, buyer_profile):
        app.include_router(resource.routes(wiring))

    @app.exception_handler(ListingError)
    def listing_error(_: Request, error: ListingError) -> JSONResponse:
        status_code, code = _ERROR_RESPONSES.get(type(error), (502, "provider_error"))
        return JSONResponse({"code": code}, status_code=status_code)

    @app.exception_handler(NotFound)
    def not_found(_: Request, error: NotFound) -> JSONResponse:
        return JSONResponse({"code": error.code}, status_code=404)

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"errors": describe_errors(list(error.errors()))})

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
