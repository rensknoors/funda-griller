# 06: Research a source of registered sale prices

**Type:** research

**What to find out:** Comparables carry asking prices, so the Expected Sale Price corrects them only by the average overbid (ADR-0004). Find a source of actual sale prices near a house: Kadaster (Kadaster-transacties, KOOPSOM via a product or open data), funda's "verkocht" listings via pyfunda (does the mobile API expose the sale price or only the last asking price?), or others. For each: cost, terms, coverage, lag, and how to fetch per address or area. Record findings under `.scratch/expected-sale-price/research/`.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] Candidate sources with cost, terms, coverage and lag
- [ ] Whether pyfunda exposes sale prices
- [ ] Recommendation: which source, if any, becomes the strongest Expected Sale Price basis
