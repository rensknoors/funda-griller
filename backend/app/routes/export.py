"""Markdown export (Exporteer als Markdown): one house's Case and current Verdict as a Dutch `.md`
file for another LLM chat. Generated from stored data only, no LLM call."""

from fastapi import APIRouter
from fastapi.responses import Response

from app import store
from app.buyer_profile import BuyerProfile
from app.case import VersionedProfile
from app.export import ExportInput, filename, render
from app.gemini_client import VERDICT_PROMPT_VERSION
from app.wiring import Wiring


def routes(w: Wiring) -> APIRouter:
    router = APIRouter(prefix="/api/listings")

    @router.get("/{funda_id}/export.md", response_model=None)
    def export_markdown(funda_id: str, profile: bool = True) -> Response:
        """`profile=false` leaves the anonymised Buyer Profile and every figure derived from it out."""
        listing = w.listing(funda_id)
        case = w.current_case(listing)
        latest = _latest_profile(w)
        export = ExportInput(
            url=listing["url"],
            snapshot=listing["snapshots"][0],
            case=case,
            verdicts=w.verdict_state(funda_id, case),
            profile=latest,
            include_profile=profile,
            verdict_prompt_version=VERDICT_PROMPT_VERSION,
            now=w.clock(),
        )
        return Response(
            render(export),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename(export)}"'},
        )

    return router


def _latest_profile(w: Wiring) -> VersionedProfile | None:
    latest = store.latest_buyer_profile(w.settings.database_path)
    return VersionedProfile(latest["version"], BuyerProfile.model_validate(latest["profile"])) if latest else None
