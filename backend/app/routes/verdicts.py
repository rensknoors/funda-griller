"""Verdicts: read a Listing's history, request a new one, and list those that are out of date."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import store
from app.assembly import make_verdict
from app.buyer_profile import BuyerProfile
from app.case import VersionedProfile
from app.ports import LlmError
from app.verdict import InvalidVerdict, changed_inputs, inputs_of
from app.wiring import Wiring

logger = logging.getLogger(__name__)


def routes(w: Wiring) -> APIRouter:
    router = APIRouter(prefix="/api")
    settings = w.settings

    def verdict_state(funda_id: str, case: dict) -> dict:
        """A Listing's Verdicts, newest first, and whether the newest is out of date (Achterhaald)."""
        history = store.verdicts(settings.database_path, funda_id)
        changed = changed_inputs(history[0], inputs_of(case, settings.verdict_model)) if history else []
        return {"verdicts": history, "out_of_date": bool(changed), "changed": changed}

    @router.get("/listings/{funda_id}/verdict", response_model=None)
    def read_verdict(funda_id: str) -> dict:
        return verdict_state(funda_id, w.current_case(w.listing(funda_id)))

    @router.post("/listings/{funda_id}/verdict", status_code=201, response_model=None)
    def run_verdict(funda_id: str) -> dict | JSONResponse:
        """Make a new Verdict version from the current Case and Buyer Profile. Never runs by itself."""
        listing = w.listing(funda_id)
        latest = store.latest_buyer_profile(settings.database_path)
        if latest is None:
            return JSONResponse({"code": "no_buyer_profile"}, status_code=409)
        case = w.current_case(listing)
        # A deal-breaker Hard no is decided without the model, so it needs no LLM client.
        if w.ports.llm_client is None and case["hard_no"] is None:
            return JSONResponse({"code": "llm_unavailable"}, status_code=503)
        profile = VersionedProfile(latest["version"], BuyerProfile.model_validate(latest["profile"]))
        now = w.clock()
        try:
            verdict = make_verdict(settings, case, profile, w.ports.llm_client, now)
        except InvalidVerdict as error:
            return JSONResponse({"code": "invalid_verdict", "problems": error.problems}, status_code=502)
        except LlmError as error:
            # The reason (no key, unknown model, quota) is the only clue to fix it, so pass it on.
            logger.warning("Verdict for %s failed: %s", funda_id, error)
            return JSONResponse({"code": "llm_unavailable", "reason": str(error)}, status_code=502)
        return store.add_verdict(settings.database_path, funda_id, now.isoformat(), verdict)

    @router.get("/verdicts/out-of-date")
    def out_of_date_verdicts() -> dict:
        """Listings whose newest Verdict is Achterhaald, e.g. to say "Dit verandert N oordelen"
        after a Buyer Profile edit. Nothing re-runs by itself."""
        out_of_date = []
        for funda_id in store.listings_with_verdicts(settings.database_path):
            state = verdict_state(funda_id, w.current_case(w.listing(funda_id)))
            if state["out_of_date"]:
                newest = state["verdicts"][0]
                out_of_date.append(
                    {"funda_id": funda_id, "verdict_id": newest["id"], "tier": newest["tier"], "changed": state["changed"]}
                )
        return {"count": len(out_of_date), "verdicts": out_of_date}

    return router
