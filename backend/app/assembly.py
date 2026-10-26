"""Case and Verdict wiring shared by the HTTP API and the Verdict regression runner, so both build
them exactly the same way: rules loaded from configuration, Source settings applied, the Walk-away
Maximum's monthly cost on the same energielabel as the Case."""

from collections.abc import Sequence
from datetime import datetime

from app.affordability import compute
from app.buyer_profile import reduce_profile
from app.case import SourceInputs, VersionedProfile, build_case
from app.gemini_client import VERDICT_PROMPT_VERSION
from app.ports import LlmClient
from app.rules_loader import load_cost_table, load_flag_rules, load_rules
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
    return build_case(
        funda_id,
        snapshot,
        profile,
        load_rules(settings.affordability_rules_path, now.year),
        load_flag_rules(settings.flag_rules_path),
        load_cost_table(settings.renovation_costs_path),
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
    rules = load_rules(settings.affordability_rules_path, now.year)
    energy_label = case["affordability"]["energy_label"] if case["affordability"] else None
    verdict = judge(
        case,
        reduce_profile(profile.version, profile.profile),
        llm_client,
        settings.verdict_model,
        WalkAwayMargins(settings.walk_away_comparables_premium, settings.walk_away_asking_price_margin),
        lambda price: compute(profile.profile, price, energy_label, rules, now.date()).monthly_cost,
    )
    return {**verdict, "prompt_version": None if verdict["deterministic"] else VERDICT_PROMPT_VERSION}
