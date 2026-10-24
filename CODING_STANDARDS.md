# Coding standards

Read during review. Judgement calls only; anything mechanical belongs in a check (the import-linter contracts in the backend config, tests, typecheck). Vocabulary comes from `GLOSSARY.md`; decisions from `docs/adr/`.

## Evidence and judgement

- Only the Verdict service judges (ADR-0001). A Case, a Flag rule or a metric that sounds like an opinion is a defect.
- Every Flag cites its rule id, rule version and evidence facts. A Flag with no evidence path is a defect.
- Every fact entering a Case carries a provenance class (Listing, Source, Observation, Finding) and a fetch or extraction time. Observations read as estimated, Findings as seller-stated, WOZ as third-party.
- LLM output is validated at the boundary: a tier outside the four, or a Walk-away Maximum above affordability, is rejected, not displayed.

## Boundaries

- Outside-world access (funda, registers, Gemini) goes through a port. A new outside dependency is a new port or Source client with a fixture-backed fake.
- Only derived Buyer Profile figures and preferences reach the LLM. Photos and Documents go out for extraction only and are shown only in the app's own UI.
- Nothing crawls, searches or bulk-fetches funda.

## Language

- Code, tickets and docs use glossary terms and avoid the terms listed under `_Avoid_`.
- UI copy is Dutch and uses each term's `_Dutch UI_` label. **Verouderd** is a Stale fact; **Achterhaald** is a Verdict or Case built on older inputs.

## Tests

- Test through the HTTP API with fakes at the three ports. Assert on observable results, not on prompts, rule internals or private functions.
