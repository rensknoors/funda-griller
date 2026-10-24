from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import store
from app.buyer_profile import BuyerProfile, describe_errors, reduce_profile, describe_errors
from app.ports import Ports
from app.production_ports import build_production_ports
from app.settings import Settings


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

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"errors": describe_errors(list(error.errors()))}
        )

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content={"errors": describe_errors(list(error.errors()))}
        )

    @app.put("/api/buyer-profile")
    def save_buyer_profile(profile: BuyerProfile) -> dict:
        return store.save_buyer_profile(settings.database_path, profile.model_dump(mode="json"))

    @app.get("/api/buyer-profile")
    def read_buyer_profile() -> dict:
        latest = store.latest_buyer_profile(settings.database_path)
        if latest is None:
            raise HTTPException(status_code=404, detail="Nog geen koperprofiel")
        return latest

    @app.get("/api/buyer-profile/versions")
    def list_buyer_profile_versions() -> list[dict]:
        return store.buyer_profile_versions(settings.database_path)

    @app.get("/api/buyer-profile/reduced")
    def read_reduced_buyer_profile() -> dict:
        latest = read_buyer_profile()
        return reduce_profile(latest["version"], BuyerProfile.model_validate(latest["profile"]))

    return app

