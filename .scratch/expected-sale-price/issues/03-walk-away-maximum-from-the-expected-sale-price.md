# 03: Walk-away Maximum from the Expected Sale Price

**What to build:** Spec "Walk-away Maximum" (decisions 5, 7). `derive_walk_away_maximum` takes the Expected Sale Price as its only price basis: `min(affordable, (expected − Direct nodig) × (1 + walk_away_premium))`. Without an Expected Sale Price there is no Walk-away Maximum. Rename `walk_away_comparables_premium` to `walk_away_premium`, default 0.05. Update the Walk-away Maximum glossary entry.

**Blocked by:** 01

**Status:** resolved

- [x] `basis` is `expected_sale_price`; `weakly_grounded` follows it
- [x] No asking price basis and no affordability-only fallback; `asking_price_margin` leaves the Case
- [x] Setting renamed, default 0.05
- [x] Unit tests: strong and weak basis, affordability binding, no Expected Sale Price → none
- [x] GLOSSARY: Walk-away Maximum rewritten
