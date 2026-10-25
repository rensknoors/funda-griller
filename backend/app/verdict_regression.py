"""Verdict regression set: stored Listings with the household's expected tier, run through the real
Verdict model on demand to gate prompt, rule and model changes.

COSTS MONEY: every non-deterministic entry is one call to the configured Verdict model. It is not
part of `pytest`; run it by hand:

    uv run python -m app.verdict_regression run --yes
    uv run python -m app.verdict_regression add <funda_id> --expect consider --name <slug>

Each entry is one JSON file in the set directory: the Listing snapshot, Source runs and Buyer
Profile frozen at the moment it was added, plus `expected_tier` and `as_of` (the clock the Case is
built against). See `config/verdict_regression/README.md`.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from app import store
from app.affordability import compute
from app.buyer_profile import BuyerProfile, reduce_profile
from app.case import build_case
from app.gemini_client import VERDICT_PROMPT_VERSION, GeminiLlmClient
from app.ports import LlmClient, LlmError
from app.rules_loader import load_flag_rules, load_rules
from app.settings import CONFIG_DIR, Settings
from app.verdict import TIERS, InvalidVerdict, judge

DEFAULT_SET = CONFIG_DIR / "verdict_regression"
DEFAULT_RESULTS = Path("data/verdict-regression")


def main(
    argv: list[str] | None = None,
    settings: Settings | None = None,
    llm_client: LlmClient | None = None,
    out: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.verdict_regression")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="Run the set against the real Verdict model (costs money).")
    run_parser.add_argument("--yes", action="store_true", help="Confirm the model calls; without it nothing runs.")
    run_parser.add_argument("--set", type=Path, default=DEFAULT_SET)
    run_parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    add_parser = commands.add_parser("add", help="Freeze a captured Listing into the set.")
    add_parser.add_argument("funda_id")
    add_parser.add_argument("--expect", required=True, choices=TIERS)
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--note", default="")
    add_parser.add_argument("--set", type=Path, default=DEFAULT_SET)
    args = parser.parse_args(argv)
    settings = settings or Settings()
    if args.command == "add":
        return _add(args, settings, out)
    return _run(args, settings, llm_client, out)


def _entries(directory: Path) -> list[tuple[str, dict]]:
    return [(path.stem, json.loads(path.read_text())) for path in sorted(directory.glob("*.json"))]


def _run(args: argparse.Namespace, settings: Settings, llm_client: LlmClient | None, out: TextIO) -> int:
    entries = _entries(args.set)
    model = settings.verdict_model
    if not args.yes:
        print(
            f"COSTS MONEY: this makes up to {len(entries)} calls to Verdict model {model}. "
            "Re-run with --yes to go ahead.",
            file=out,
        )
        return 2
    llm_client = llm_client or GeminiLlmClient(settings.gemini_api_key, settings.vision_model, model)
    flag_rules = load_flag_rules(settings.flag_rules_path)
    print(
        f"Verdict model: {model} | flag rule set version: {flag_rules.version} | "
        f"prompt version: {VERDICT_PROMPT_VERSION}",
        file=out,
    )
    results = []
    for name, data in entries:
        actual, error, deterministic = _judge(name, data, settings, llm_client, flag_rules)
        expected = data["expected_tier"]
        outcome = "ERROR" if error else "OK" if actual == expected else "DIFF"
        results.append(
            {
                "name": name,
                "expected": expected,
                "actual": actual,
                "outcome": outcome,
                "error": error,
                "deterministic": deterministic,
            }
        )
        shown = error or actual
        suffix = " (deterministic, no model call)" if deterministic else ""
        print(f"{outcome:<5} {name:<40} expected {expected:<9} actual {shown}{suffix}", file=out)
    agreed = sum(result["outcome"] == "OK" for result in results)
    print(f"Agreement: {agreed}/{len(results)}", file=out)
    run_at = datetime.now(UTC)
    record = {
        "run_at": run_at.isoformat(),
        "model": model,
        "flag_rules_version": flag_rules.version,
        "prompt_version": VERDICT_PROMPT_VERSION,
        "agreed": agreed,
        "total": len(results),
        "results": results,
    }
    args.results.mkdir(parents=True, exist_ok=True)
    path = args.results / f"{run_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(f"Results: {path}", file=out)
    return 0 if agreed == len(results) else 1


def _judge(
    name: str, data: dict, settings: Settings, llm_client: LlmClient, flag_rules
) -> tuple[str | None, str | None, bool]:
    """(actual tier, error, deterministic) for one entry, built exactly as the app builds a Case."""
    now = datetime.fromisoformat(data["as_of"])
    rules = load_rules(settings.affordability_rules_path, now.year)
    profile = BuyerProfile.model_validate(data["buyer_profile"])
    case = build_case(
        name,
        {**data["snapshot"], "id": name},
        0,
        profile,
        rules,
        flag_rules,
        now,
        list(data["source_runs"]),
        {source: {"latest": run, "last_success": run} for source, run in data["source_runs"].items()},
        settings.source_ttl_days,
        settings.comparables_min_count,
    )
    try:
        verdict = judge(
            case,
            reduce_profile(0, profile),
            llm_client,
            settings.verdict_model,
            settings.walk_away_comparables_premium,
            lambda price: compute(profile, price, None, rules, now.date()).monthly_cost,
        )
    except InvalidVerdict as error:
        return None, f"invalid_verdict: {error}", False
    except LlmError as error:
        return None, f"llm_unavailable: {error}", False
    return verdict["tier"], None, verdict["deterministic"]


def _add(args: argparse.Namespace, settings: Settings, out: TextIO) -> int:
    """Freeze a captured Listing's newest snapshot, its last good Source runs and the newest Buyer
    Profile into a new entry, so later runs see exactly the same inputs."""
    if not settings.database_path.exists():
        print(f"No database at {settings.database_path}, so no captured Listing {args.funda_id}.", file=out)
        return 1
    listing = store.get_listing(settings.database_path, args.funda_id)
    profile = store.latest_buyer_profile(settings.database_path)
    path = args.set / f"{args.name}.json"
    if listing is None:
        print(f"No captured Listing {args.funda_id}.", file=out)
        return 1
    if profile is None:
        print("No Buyer Profile saved yet.", file=out)
        return 1
    if path.exists():
        print(f"{path} already exists.", file=out)
        return 1
    snapshot = {key: value for key, value in listing["snapshots"][0].items() if key != "id"}
    runs = store.source_runs(settings.database_path, args.funda_id)
    entry = {
        "expected_tier": args.expect,
        "note": args.note,
        "as_of": datetime.now(UTC).isoformat(),
        "snapshot": snapshot,
        "source_runs": {source: run["last_success"] for source, run in runs.items() if run["last_success"]},
        "buyer_profile": profile["profile"],
    }
    args.set.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")
    print(f"Added {args.name} (Listing {args.funda_id}, expected {args.expect}) to {path}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
