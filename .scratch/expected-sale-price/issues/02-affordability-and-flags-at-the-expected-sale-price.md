# 02: Affordability and price Flags at the Expected Sale Price

**What to build:** Spec "Affordability and Flags" (decision 8). Headroom and monthly costs are measured at the Expected Sale Price. Replace `ask_beyond_headroom` with `expected_price_beyond_headroom` (same deal-breaker aliases); its Hard no applies only on a strongly grounded Expected Sale Price. Remove `ask_far_above_woz` and `ask_far_above_comparables`. Bump the Flag rule set version.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `affordability.headroom` = affordable maximum − Expected Sale Price; null without one
- [ ] `monthly_cost`/`monthly_cost_net` at the Expected Sale Price
- [ ] `expected_price_beyond_headroom` raises at headroom < 0 on either basis, silent without an Expected Sale Price
- [ ] Deal-breaker Hard no via its aliases only when the Expected Sale Price is strongly grounded
- [ ] The two asking-price Flags removed; rule set `version` bumped; earlier Verdicts show as Achterhaald
- [ ] Scenario tests: over-asked house within reach (no Flag, no Hard no); under-asked house beyond reach (Flag; Hard no on a strong basis only)
- [ ] Comparison payload (`comparison.py`) carries headroom at the Expected Sale Price and `asking_vs_expected_percent`
- [ ] GLOSSARY: Hard no notes the strong-basis condition for price deal-breakers
