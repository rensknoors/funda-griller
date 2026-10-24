# 14: Comparables and Walk-away Maximum grounding

**What to build:** Nearby comparable listings (from the provider's similar-listings IDs, followed up with a small, user-triggered, capped number of fetches) give the Case an ask-versus-comparables metric, and the Walk-away Maximum in the Bid Advice is grounded in comparables plus affordability instead of affordability alone.

**Blocked by:** 07 (Energielabel and WOZ Sources), 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

- [ ] Comparable listings are fetched only on user action and capped at a small configured number
- [ ] The Case shows ask versus comparables as a computed metric, with the comparables listed
- [ ] The Walk-away Maximum takes comparables into account and never exceeds affordability
- [ ] Thin or missing comparables are stated in the Case rather than hidden
- [ ] Fixture-based API tests cover several comparables, a single comparable and none
