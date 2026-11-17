# 08: Time on the market in the Guide Bid

**What to build:** ADR-0005. Days on the market (first `price_history` date to the snapshot's fetch date) and a price reduction (first price above the current asking price) raise the Guide Bid's discount: over 60 days +1 point, over 120 days +2 points (not cumulative), a price reduction +1 point, total discount capped at 10%. All configurable in `defaults.toml`. Without `price_history` the signal does not count and the Biedadvies says the tempo is unknown.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] Tempo signal derived from `price_history` in the Case; unit tests at 60 and 120 days, with and without a price reduction, the 10% cap, missing or empty history
- [ ] Discount breakdown shows days on the market and the reduction
- [ ] "Tempo onbekend" in the Biedadvies when there is no history
- [ ] Regression case: a house on the market for 120+ days with a price reduction
- [ ] Prompt and Case versions bumped as needed
