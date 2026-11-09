"""Case and Verdict wiring shared by the HTTP API and the Verdict regression runner, so both build
them exactly the same way: rules loaded from configuration, Source settings applied, the Walk-away
Maximum's monthly cost on the same energielabel as the Case."""

from collections.abc import Sequence
from datetime import datetime

from app.affordability import Affordability, compute
from app.buyer_profile import reduce_profile
from app.case import SourceInputs, VersionedProfile, build_case
from app.gemini_client import VERDICT_PROMPT_VERSION
from app.ports import LlmClient
from app.rules_loader import (
    expected_levering,
    load_bid_margins,
    load_cost_table,
    load_flag_rules,
    load_price_index,
    load_rules,
)
from app.settings import Settings
from app.verdict import WalkAwayMargins, judge


def assemble_case(
    settings: Settings,
    funda_id: str,
    snapshot: dict,
    profile: VersionedProfile | None,
    now: datetime,
    source_names: list[str],
    source_runs: dict[str, dict],
    observation_runs: dict | None = None,
    documents: Sequence[dict] = (),
) -> dict:
    sources = SourceInputs(source_names, source_runs, settings.source_ttl_days, settings.comparables_min_count)
    levering = expected_levering(now.date(), settings.expected_levering_months)
    return build_case(
        funda_id,
        snapshot,
        profile,
        load_rules(settings.affordability_rules_path, levering.year),
        levering,
        load_flag_rules(settings.flag_rules_path),
        load_cost_table(settings.renovation_costs_path),
        load_price_index(settings.price_index_path),
        load_bid_margins(settings.bid_margins_path),
        now,
        sources,
        observation_runs,
        documents,
    )


def make_verdict(
    settings: Settings, case: dict, profile: VersionedProfile, llm_client: LlmClient | None, now: datetime
) -> dict:
    """A Verdict for the Case. Raises InvalidVerdict or LlmError (also when the Case needs the model
    and there is no LLM client); a deal-breaker Hard no needs neither. A model Verdict records the
    prompt version it was made with."""
    levering = expected_levering(now.date(), settings.expected_levering_months)
    rules = load_rules(settings.affordability_rules_path, levering.year)
    affordability = case["affordability"] or {}
    energy_label = affordability.get("energy_label")
    renovation_direct = affordability.get("renovation_direct", 0)
    verdict = judge(
        case,
        reduce_profile(profile.version, profile.profile),
        llm_client,
        settings.verdict_model,
        WalkAwayMargins(settings.walk_away_comparables_premium),
        lambda price: _monthly_costs_at(compute(profile.profile, price, energy_label, rules, levering, renovation_direct)),
    )
    return {**verdict, "prompt_version": None if verdict["deterministic"] else VERDICT_PROMPT_VERSION}


def _monthly_costs_at(affordability: Affordability) -> dict:
    return {"gross": affordability.monthly_cost, "net": affordability.monthly_cost_net}
