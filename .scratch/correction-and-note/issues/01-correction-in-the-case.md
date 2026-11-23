# 01: Correction in the Case

**Type:** task

**Blocked by:** none

**Status:** resolved

**What to build:** Spec decisions 2–8. The user's own value for a Listing fact the Case computes with (living area, plot area, build year, house type, energielabel, ownership situation, rooms, bedrooms), stored with a required explanation. It is applied before the Case derives anything, so every figure uses it. The original stays visible, and the model sees both values plus the explanation.

- [x] `corrections` storage per house and fact key, with value, explanation, `created_at` and `listing_value_at_correction`; one live Correction per fact
- [x] `PUT` and `DELETE /listings/{funda_id}/corrections/{key}` with per-key validation; unknown keys and an empty explanation are rejected
- [x] The Case applies Corrections before deriving: tests show that a corrected living area changes `asking_vs_comparables`, the Expected Sale Price (value and low–high), the Prijsstelling, the Renovation Estimate's sized items, the Walk-away Maximum and the Guide Bid
- [x] A corrected `house_type` changes which comparables count; a corrected energielabel outranks the register's
- [x] A Correction fills a missing fact (original shown as unknown)
- [x] The fact carries provenance `correction`, `original` (value, provenance) and `explanation`; the model's view of the Case includes them
- [x] After a re-capture the Correction stays; `listing_changed` is true when the Listing's value has moved since the Correction was made
- [x] A Correction change makes the Verdict Achterhaald (cause `case`)
- [x] Regression case: a house whose living area is corrected downward
- [x] Prompt version bumped if the prompt text changes

## Comments

- 2026-11-23: Built test-first through the HTTP API (`backend/tests/test_corrections_api.py`, regression harness tests in `test_verdict_regression.py`). Validation lives in `case.corrected_value`; the routes answer the new Case, and reject with 422 `not_correctable`, `invalid_value` or `explanation_required` (DELETE of a missing Correction is 404). A corrected energielabel's `original` is the register's label when there is one, else the Listing's. `built_from.corrections` (key, value, `created_at`) drives Achterhaald with cause `case`. The prompt text did not change (the model learns the class from a new `correction` entry in the provenance legend), so `VERDICT_PROMPT_VERSION` stays at 12. The regression entry is `config/verdict_regression/example-corrected-living-area.json` (128 m² corrected to 112 m²); the harness and `add` carry `corrections`. Left for ticket 04: the Markdown export still lists only `listing` facts, so a corrected fact is missing from its Listing section until then.
