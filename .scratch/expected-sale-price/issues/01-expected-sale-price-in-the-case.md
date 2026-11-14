# 01: Expected Sale Price and Prijsstelling in the Case

**What to build:** Spec "Expected Sale Price" and "Prijsstelling" (decisions 1–4). Add the Case metrics `expected_sale_price` (comparables + average overbid, else indexed WOZ, else null) and `asking_vs_expected` (gap and band label). Split WOZ indexing from `_asking_vs_woz` so the WOZ basis works without an asking price. Rework the `config/bid_margins.toml` header. Add both terms to `GLOSSARY.md` and update Comparable.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] `expected_sale_price` per spec shape, with basis, overbid source, low/high range and `weakly_grounded`
- [ ] No asking price fallback: neither sufficient comparables nor WOZ gives `value: null`
- [ ] WOZ basis works for a Listing without an asking price
- [ ] `asking_vs_expected` with `prijsstelling_band` (default 0.05), null when either side is missing
- [ ] Unit tests per basis and at the band edges
- [ ] GLOSSARY: Expected Sale Price, Prijsstelling; Comparable updated
