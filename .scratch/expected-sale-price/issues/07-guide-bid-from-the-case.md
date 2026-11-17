# 07: Guide Bid from the Expected Sale Price and Prijsstelling

**What to build:** ADR-0005. The Case derives a Guide Bid (Richtbod) = `min(asking price, expected_sale_price × (1 − discount))`, capped at the Walk-away Maximum, rounded down to €500. Discount by Prijsstelling (configurable in `defaults.toml`): hoog ingezet 5–7%, marktconform 2–3%, laag ingezet 0%. The Guide Bid goes into the model's input; the prompt tells the model to bid within ±3% of it and explain any deviation. The Biedadvies shows the Openingsbod, and the Richtbod with the model's reason when they differ, plus the discount breakdown. Same discount on a weakly grounded Expected Sale Price, flagged as such. No Guide Bid without a Walk-away Maximum or for a house sold under reservation (conditions only, with a note).

**Blocked by:** 04

**Status:** resolved

- [x] `guide_bid` derivation in the Case with its discount breakdown; unit tests per Prijsstelling band, the asking-price cap, the Walk-away Maximum cap, rounding, weakly grounded basis, none without a Walk-away Maximum, none when sold under reservation
- [x] Prompt: bid within ±3% of the Guide Bid, deviations explained; `VERDICT_PROMPT_VERSION` bumped
- [x] Validation: opening bid outside the band is a problem; the existing `opening_bid_above_walk_away_maximum` stays
- [x] Bid Advice carries `guide_bid` and its derivation; older Verdicts still render
- [x] UI (Dutch) and Markdown export: Openingsbod, Richtbod when different, discount breakdown, "Verkocht onder voorbehoud" note
- [x] Regression cases added with expected tier and opening-bid range: `example-guide-bid-marktconform`, `-hoog-ingezet`, `-laag-ingezet`
- [ ] Real-model run of the regression set (user, costs money): not done by the agent
- [x] Glossary and ADR-0005 stay in line with the result

## Comments

Built on `ticket/07-guide-bid`. Everything but the real-model regression run is done, so the Status stays open: the user runs `uv run python -m app.verdict_regression run --yes` (costs money) and tunes `[guide_bid]` in `config/defaults.toml` if the three new `example-guide-bid-*` entries disagree. Deviation: the model's `deviation_reason` is stored and shown but not required by validation.

Resolved after the code review (branch `fix/review-findings`), like ticket 04: the real-model regression run stays with the user (`uv run python -m app.verdict_regression run --yes`, costs money). The review made `deviation_reason` required (a different opening bid without one is `deviation_reason_missing`) and rejects an opening bid above the asking price (`opening_bid_above_asking_price`); sold under reservation is now the Listing status `sold_under_reservation`. `VERDICT_PROMPT_VERSION` is 11.
