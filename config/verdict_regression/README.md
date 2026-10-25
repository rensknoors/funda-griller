# Verdict regression set

Stored Listings with the tier the household expects. Run them through the real Verdict model before
changing the Verdict prompt (`VERDICT_PROMPT_VERSION` in `backend/app/gemini_client.py`), the Flag
rule set (`config/flag_rules.toml`) or the Verdict model (`verdict_model`), and compare.

**Running the set costs money:** one Verdict model call per entry that is not a deterministic Hard no.
It is not part of `pytest`.

```
cd backend
uv run python -m app.verdict_regression run          # says how many calls it would make, runs nothing
uv run python -m app.verdict_regression run --yes    # runs the set against the configured model
```

It prints expected versus actual per entry and the agreement, and writes the same plus the model id,
Flag rule set version and prompt version to `backend/data/verdict-regression/<time>.json`. Exit code
0 means every entry agreed, 1 means at least one differed or failed.

## The seed entries are placeholders

The `example-*.json` files are fictional Listings with guessed tiers, there to show the format and
keep the harness tested. Replace them with real Listings you have judged yourself, then delete them.
Aim for 5 to 10 entries that cover every tier.

## Adding a real Listing

Capture the Listing in the app and save your Buyer Profile, then:

```
cd backend
uv run python -m app.verdict_regression add <funda_id> --expect consider --name <short-slug> --note "why"
```

This freezes the newest snapshot, the last good run of each Source, the photo Observation run, the
Documents with their Findings and the newest Buyer Profile into
`config/verdict_regression/<short-slug>.json`, so later runs see the same inputs even after the
Listing or profile changes. `--expect` is one of `must_buy`, `consider`, `skip`, `hard_no`.

## Entry format

One JSON file per entry; the file name is its name.

- `expected_tier`: the tier you would give it.
- `note`: free text, why you expect that tier.
- `as_of`: the moment the Case is built against (affordability rules year, Source staleness).
- `snapshot`: the Listing snapshot as the app stores it (`fetched_at` required).
- `source_runs`: per Source, `{attempted_at, outcome, reason, facts: [{name, value, as_of}]}`.
- `observation_run` (optional): the last good photo Observation run, `{id, attempted_at, outcome,
  reason, model, observations}`; `snapshot.photos` lists the photos it cites.
- `documents` (optional): the Listing's Documents as the app stores them, with their `findings`.
- `buyer_profile`: a full Buyer Profile as `PUT /api/buyer-profile` accepts it. Only its reduced form
  reaches the model.

You can edit `expected_tier` and `note` by hand; editing the frozen inputs changes what is tested.
