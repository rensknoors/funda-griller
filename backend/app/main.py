from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from app import documents, store
from app.affordability import compute, consequences
from app.case import build_case
from app.buyer_profile import BuyerProfile, FinanceDraft, describe_errors, reduce_profile
from app.comparison import summarise
from app.listing_url import funda_id_from_url
from app.manual_provider import ManualEntry, ManualListingProvider
from app.ports import (
    InvalidListingUrl,
    LlmError,
    ListingError,
    ListingProvider,
    ListingRemoved,
    Ports,
    ProviderBlocked,
)
from app.observations import observe
from app.photos import keep_photos, photo_set
from app.rules_loader import load_flag_rules, load_rules
from app.production_ports import build_production_ports
from app.settings import Settings
from app.source_runner import run_sources
from app.verdict import InvalidVerdict, changed_inputs, inputs_of, judge

# Sources fetched only when the user asks for them, never on capture or a Listing refetch:
# comparables cost one provider fetch per comparable.
ON_REQUEST_SOURCES = frozenset({"comparables"})

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
        ownership_situation: str | None = None
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
        observe_photos(funda_id, photos, fetched_at)
        attach_brochure(funda_id, listing.brochure_url, fetched_at)
        return with_comparison(store.get_listing(settings.database_path, funda_id))

    def attach_brochure(funda_id: str, url: str | None, now: str) -> None:
        """Download the funda brochure as a Document, once per brochure URL. A new URL replaces the
        old brochure and its Findings."""
        if not url or ports.document_downloader is None:
            return
        brochures = [d for d in store.documents(settings.database_path, funda_id) if d["kind"] == "brochure"]
        if any(d["source_url"] == url for d in brochures):
            return
        for old in brochures:
            discard_document(funda_id, old)
        document_id = store.add_document(settings.database_path, funda_id, "brochure", "Brochure (funda)", now)
        store.update_document(settings.database_path, document_id, source_url=url)
        documents.download_and_analyse(
            settings.database_path, settings.media_dir, funda_id,
            store.get_document(settings.database_path, funda_id, document_id),
            ports.document_downloader, ports.llm_client, settings.vision_model, now,
        )

    def observe_photos(funda_id: str, photos: list[dict], at: str, rerun: bool = False) -> str | None:
        return observe(
            settings.database_path,
            settings.media_dir,
            ports.llm_client,
            settings.vision_model,
            funda_id,
            photos,
            at,
            rerun,
        )

    def with_comparison(listing: dict) -> dict:
        """The Listing plus its comparison-view row: the latest Verdict's tier, or none until a
        Verdict exists. A deal-breaker Hard no in the Case overrides it."""
        verdicts = store.verdicts(settings.database_path, listing["funda_id"])
        tier = verdicts[0]["tier"] if verdicts else None
        return {**listing, "comparison": summarise(listing["snapshots"], current_case(listing), tier)}

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

    @app.post("/api/listings/{funda_id}/observations", response_model=None)
    def rerun_observations(funda_id: str) -> dict | JSONResponse:
        """Re-run the vision model over the latest snapshot's photos, e.g. after a model change."""
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        photos = listing["snapshots"][0].get("photos", [])
        if not photos:
            return JSONResponse({"code": "no_photos"}, status_code=409)
        if ports.llm_client is None:
            return JSONResponse({"code": "llm_unavailable"}, status_code=503)
        if observe_photos(funda_id, photos, clock().isoformat(), rerun=True) == "failed":
            return JSONResponse({"code": "llm_unavailable"}, status_code=502)
        return current_case(listing)

    def current_case(listing: dict) -> dict:
        funda_id = listing["funda_id"]
        latest = store.latest_buyer_profile(settings.database_path)
        now = clock()
        identity = photo_set(listing["snapshots"][0].get("photos", []))
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
            settings.comparables_min_count,
            observation_runs=(
                store.observation_runs(settings.database_path, funda_id, identity) if identity else None
            ),
            documents=store.documents(settings.database_path, funda_id),
        )

    def document_or_404(funda_id: str, document_id: int) -> dict:
        document = store.get_document(settings.database_path, funda_id, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="not_found")
        return document

    def public_document(funda_id: str, document_id: int) -> dict:
        document = store.get_document(settings.database_path, funda_id, document_id)
        hidden = {"stored_name", "sha256", "funda_id"}
        return {key: value for key, value in document.items() if key not in hidden}

    @app.get("/api/listings/{funda_id}/documents", response_model=None)
    def list_documents(funda_id: str) -> list[dict] | JSONResponse:
        if store.get_listing(settings.database_path, funda_id) is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return [public_document(funda_id, d["id"]) for d in store.documents(settings.database_path, funda_id)]

    @app.post("/api/listings/{funda_id}/documents", status_code=201, response_model=None)
    def upload_document(funda_id: str, file: Annotated[UploadFile, File()]) -> dict | JSONResponse:
        """Add a Document (Vragenlijst, Lijst van zaken, ...) and extract its Findings once."""
        if store.get_listing(settings.database_path, funda_id) is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        now = clock().isoformat()
        document_id = store.add_document(
            settings.database_path, funda_id, "upload", (file.filename or "Document").strip() or "Document", now
        )
        document = store.get_document(settings.database_path, funda_id, document_id)
        documents.store_content(
            settings.database_path, settings.media_dir, funda_id, document, file.file.read(),
            ports.llm_client, settings.vision_model, now,
        )
        return public_document(funda_id, document_id)

    @app.put("/api/listings/{funda_id}/documents/{document_id}", response_model=None)
    def replace_document(funda_id: str, document_id: int, file: Annotated[UploadFile, File()]) -> dict:
        """Re-upload: the new file replaces the old one and its Findings."""
        document = document_or_404(funda_id, document_id)
        if file.filename and document["kind"] == "upload":
            store.update_document(settings.database_path, document_id, name=file.filename.strip() or document["name"])
        documents.store_content(
            settings.database_path, settings.media_dir, funda_id, document, file.file.read(),
            ports.llm_client, settings.vision_model, clock().isoformat(),
        )
        return public_document(funda_id, document_id)

    @app.post("/api/listings/{funda_id}/documents/{document_id}/analyse", response_model=None)
    def reanalyse_document(funda_id: str, document_id: int) -> dict:
        """Retry a Document that was not analysed, or whose brochure download failed."""
        document = document_or_404(funda_id, document_id)
        now = clock().isoformat()
        if document["status"] == "download_failed" and ports.document_downloader is not None:
            documents.download_and_analyse(
                settings.database_path, settings.media_dir, funda_id, document,
                ports.document_downloader, ports.llm_client, settings.vision_model, now,
            )
        elif document["status"] != "download_failed":
            documents.analyse(
                settings.database_path, settings.media_dir, funda_id, document_id,
                ports.llm_client, settings.vision_model, now,
            )
        return public_document(funda_id, document_id)

    @app.delete("/api/listings/{funda_id}/documents/{document_id}", status_code=204)
    def remove_document(funda_id: str, document_id: int) -> Response:
        discard_document(funda_id, document_or_404(funda_id, document_id))
        return Response(status_code=204)

    def discard_document(funda_id: str, document: dict) -> None:
        """Remove a Document's file and row; its Findings leave the Case with it."""
        store.delete_document_file(settings.media_dir, funda_id, document["stored_name"])
        store.delete_document(settings.database_path, document["id"])

    @app.get("/api/listings/{funda_id}/documents/{document_id}/file", response_model=None)
    def read_document_file(funda_id: str, document_id: int) -> FileResponse | JSONResponse:
        """The Document itself, for the app's own UI only: shown inline, never offered elsewhere."""
        document = document_or_404(funda_id, document_id)
        path = store.document_file_path(settings.media_dir, funda_id, document["stored_name"])
        if path is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return FileResponse(
            path,
            media_type="application/pdf",
            content_disposition_type="inline",
            filename=document["name"],
            headers={"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"},
        )

    def verdict_state(funda_id: str, case: dict) -> dict:
        """A Listing's Verdicts, newest first, and whether the newest is out of date (Achterhaald)."""
        history = store.verdicts(settings.database_path, funda_id)
        changed = changed_inputs(history[0], inputs_of(case, settings.verdict_model)) if history else []
        return {"verdicts": history, "out_of_date": bool(changed), "changed": changed}

    @app.get("/api/listings/{funda_id}/verdict", response_model=None)
    def read_verdict(funda_id: str) -> dict | JSONResponse:
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        return verdict_state(funda_id, current_case(listing))

    @app.post("/api/listings/{funda_id}/verdict", status_code=201, response_model=None)
    def run_verdict(funda_id: str) -> dict | JSONResponse:
        """Make a new Verdict version from the current Case and Buyer Profile. Never runs by itself."""
        listing = store.get_listing(settings.database_path, funda_id)
        if listing is None:
            return JSONResponse({"code": "not_found"}, status_code=404)
        latest = store.latest_buyer_profile(settings.database_path)
        if latest is None:
            return JSONResponse({"code": "no_buyer_profile"}, status_code=409)
        case = current_case(listing)
        # A deal-breaker Hard no is decided without the model, so it needs no LLM client.
        if ports.llm_client is None and case["hard_no"] is None:
            return JSONResponse({"code": "llm_unavailable"}, status_code=503)
        profile = BuyerProfile.model_validate(latest["profile"])
        now = clock()
        rules = load_rules(settings.affordability_rules_path, now.year)
        energy_label = case["affordability"]["energy_label"]
        try:
            verdict = judge(
                case,
                reduce_profile(latest["version"], profile),
                ports.llm_client,
                settings.verdict_model,
                settings.walk_away_comparables_premium,
                lambda price: compute(profile, price, energy_label, rules, now.date()).monthly_cost,
            )
        except InvalidVerdict as error:
            return JSONResponse({"code": "invalid_verdict", "problems": error.problems}, status_code=502)
        except LlmError:
            return JSONResponse({"code": "llm_unavailable"}, status_code=502)
        return store.add_verdict(settings.database_path, funda_id, now.isoformat(), verdict)

    @app.get("/api/verdicts/out-of-date")
    def out_of_date_verdicts() -> dict:
        """Listings whose newest Verdict is Achterhaald, e.g. to say "Dit verandert N oordelen"
        after a Buyer Profile edit. Nothing re-runs by itself."""
        out_of_date = []
        for funda_id in store.listings_with_verdicts(settings.database_path):
            listing = store.get_listing(settings.database_path, funda_id)
            state = verdict_state(funda_id, current_case(listing))
            if state["out_of_date"]:
                newest = state["verdicts"][0]
                out_of_date.append(
                    {"funda_id": funda_id, "verdict_id": newest["id"], "tier": newest["tier"], "changed": state["changed"]}
                )
        return {"count": len(out_of_date), "verdicts": out_of_date}

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

    @app.post("/api/buyer-profile/validation")
    def check_buyer_profile(draft: dict = Body()) -> dict:
        try:
            BuyerProfile.model_validate(draft)
        except ValidationError as error:
            return {"errors": describe_errors(list(error.errors()))}
        return {"errors": []}

    @app.post("/api/buyer-profile/consequences")
    def work_out_consequences(draft: FinanceDraft) -> dict:
        today = clock().date()
        rules = load_rules(settings.affordability_rules_path, today.year)
        return {
            **asdict(consequences(draft, rules, today)),
            "rules": {"year": rules.year, "is_current_year": rules.year == today.year},
        }

    @app.get("/api/buyer-profile/reduced")
    def read_reduced_buyer_profile() -> dict:
        latest = latest_or_404()
        return reduce_profile(latest["version"], BuyerProfile.model_validate(latest["profile"]))

    return app

