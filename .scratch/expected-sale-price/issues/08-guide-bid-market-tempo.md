# 08: Time on the market in the Guide Bid

**What to build:** ADR-0005. Days on the market (first `price_history` date to the snapshot's fetch date) and a price reduction (first price above the current asking price) raise the Guide Bid's discount: over 60 days +1 point, over 120 days +2 points (not cumulative), a price reduction +1 point, total discount capped at 10%. All configurable in `defaults.toml`. Without `price_history` the signal does not count and the Biedadvies says the tempo is unknown.

**Blocked by:** 07

**Status:** ready-for-agent

- [x] Tempo signal derived from `price_history` in the Case; unit tests at 60 and 120 days, with and without a price reduction, the 10% cap, missing or empty history
- [x] Discount breakdown shows days on the market and the reduction
- [x] "Tempo onbekend" in the Biedadvies when there is no history
- [x] Regression case: a house on the market for 120+ days with a price reduction
- [x] Prompt and Case versions bumped as needed
- [ ] Real-model run of the regression set (user, costs money): not done by the agent

## Comments

Built on `ticket/08-guide-bid-tempo`. Everything but the real-model regression run is done, so the Status stays open, as with ticket 07: the user runs `uv run python -m app.verdict_regression run --yes` (costs money) and tunes `[guide_bid]` in `config/defaults.toml` if `example-guide-bid-tempo` (137 days, 565.000 to 535.000, Richtbod 500.000, expected opening bid 485.000-515.000) disagrees.

- The Case carries a new metric `market_tempo` (`listed_on`, `days_on_market`, `first_asking_price`, `asking_price`, `price_reduction`), null without a readable first `price_history` date. Dates are read in funda's Dutch form ("15 apr 2026") and ISO.
- The Guide Bid's breakdown gains `days_on_market` and `price_reduction` (the latter labelled "geen" with 0% when there is none), plus `tempo_known` and `discount_capped`.
- `VERDICT_PROMPT_VERSION` is 10. There is no separate Case version in the code: the Case shape change is covered by the prompt version, and the tempo rests only on the snapshot, already part of a Verdict's inputs.
- The e2e Richtbod woning Kerkpad 2 now has no price history (it ran on the real clock, so its fixed history date would cross 60 days and change its Richtbod); the tempo woning Kerkpad 4 dates its history relative to today.
