"""The Buyer Profile: read, save as a new version, validate a draft, and work out its consequences."""

from dataclasses import asdict

from fastapi import APIRouter, Body
from pydantic import ValidationError

from app import store
from app.affordability import consequences
from app.buyer_profile import BuyerProfile, FinanceDraft, describe_errors, reduce_profile
from app.rules_loader import load_rules
from app.wiring import Wiring


def routes(w: Wiring) -> APIRouter:
    router = APIRouter(prefix="/api/buyer-profile")
    settings = w.settings

    @router.put("")
    def save_buyer_profile(profile: BuyerProfile) -> dict:
        return store.save_buyer_profile(settings.database_path, profile.model_dump(mode="json"))

    @router.get("")
    def read_buyer_profile() -> dict:
        return w.buyer_profile()

    @router.get("/versions")
    def list_buyer_profile_versions() -> list[dict]:
        return store.buyer_profile_versions(settings.database_path)

    @router.post("/validation")
    def check_buyer_profile(draft: dict = Body()) -> dict:
        try:
            BuyerProfile.model_validate(draft)
        except ValidationError as error:
            return {"errors": describe_errors(list(error.errors()))}
        return {"errors": []}

    @router.post("/consequences")
    def work_out_consequences(draft: FinanceDraft) -> dict:
        today = w.clock().date()
        rules = load_rules(settings.affordability_rules_path, today.year)
        return {
            **asdict(consequences(draft, rules, today)),
            "rules": {"year": rules.year, "is_current_year": rules.year == today.year},
        }

    @router.get("/reduced")
    def read_reduced_buyer_profile() -> dict:
        latest = w.buyer_profile()
        return reduce_profile(latest["version"], BuyerProfile.model_validate(latest["profile"]))

    return router
