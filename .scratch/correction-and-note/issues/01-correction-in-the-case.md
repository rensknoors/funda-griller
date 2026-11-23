# 01: Correction in the Case

**Type:** task

**Blocked by:** none

**Status:** ready-for-agent

**What to build:** Spec decisions 2–8. The user's own value for a Listing fact the Case computes with (living area, plot area, build year, house type, energielabel, ownership situation, rooms, bedrooms), stored with a required explanation. It is applied before the Case derives anything, so every figure uses it. The original stays visible, and the model sees both values plus the explanation.

- [ ] `corrections` storage per house and fact key, with value, explanation, `created_at` and `listing_value_at_correction`; one live Correction per fact
- [ ] `PUT` and `DELETE /listings/{funda_id}/corrections/{key}` with per-key validation; unknown keys and an empty explanation are rejected
- [ ] The Case applies Corrections before deriving: tests show that a corrected living area changes `asking_vs_comparables`, the Expected Sale Price (value and low–high), the Prijsstelling, the Renovation Estimate's sized items, the Walk-away Maximum and the Guide Bid
- [ ] A corrected `house_type` changes which comparables count; a corrected energielabel outranks the register's
- [ ] A Correction fills a missing fact (original shown as unknown)
- [ ] The fact carries provenance `correction`, `original` (value, provenance) and `explanation`; the model's view of the Case includes them
- [ ] After a re-capture the Correction stays; `listing_changed` is true when the Listing's value has moved since the Correction was made
- [ ] A Correction change makes the Verdict Achterhaald (cause `case`)
- [ ] Regression case: a house whose living area is corrected downward
- [ ] Prompt version bumped if the prompt text changes

## Comments
