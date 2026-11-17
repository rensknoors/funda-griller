# 07: Guide Bid from the Expected Sale Price and Prijsstelling

**What to build:** ADR-0005. The Case derives a Guide Bid (Richtbod) = `min(asking price, expected_sale_price × (1 − discount))`, capped at the Walk-away Maximum, rounded down to €500. Discount by Prijsstelling (configurable in `defaults.toml`): hoog ingezet 5–7%, marktconform 2–3%, laag ingezet 0%. The Guide Bid goes into the model's input; the prompt tells the model to bid within ±3% of it and explain any deviation. The Biedadvies shows the Openingsbod, and the Richtbod with the model's reason when they differ, plus the discount breakdown. Same discount on a weakly grounded Expected Sale Price, flagged as such. No Guide Bid without a Walk-away Maximum or for a house sold under reservation (conditions only, with a note).

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] `guide_bid` derivation in the Case with its discount breakdown; unit tests per Prijsstelling band, the asking-price cap, the Walk-away Maximum cap, rounding, weakly grounded basis, none without a Walk-away Maximum, none when sold under reservation
- [ ] Prompt: bid within ±3% of the Guide Bid, deviations explained; `VERDICT_PROMPT_VERSION` bumped
- [ ] Validation: opening bid outside the band is a problem; the existing `opening_bid_above_walk_away_maximum` stays
- [ ] Bid Advice carries `guide_bid` and its derivation; older Verdicts still render
- [ ] UI (Dutch) and Markdown export: Openingsbod, Richtbod when different, discount breakdown, "Verkocht onder voorbehoud" note
- [ ] Regression cases: Europalaan-26-like (marktconform), hoog ingezet (far below asking), laag ingezet (at asking); real-model run (user, costs money)
- [ ] Glossary and ADR-0005 stay in line with the result
