# 14: Comparables and Walk-away Maximum grounding

**What to build:** Nearby comparable listings (from the provider's similar-listings IDs, followed up with a small, user-triggered, capped number of fetches) give the Case an ask-versus-comparables metric, and the Walk-away Maximum in the Bid Advice is grounded in comparables plus affordability instead of affordability alone.

**Blocked by:** 07 (Energielabel and WOZ Sources), 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] Comparable listings are fetched only on user action and capped at a small configured number
- [x] The Case shows ask versus comparables as a computed metric, with the comparables listed
- [x] The Walk-away Maximum takes comparables into account and never exceeds affordability
- [x] Thin or missing comparables are stated in the Case rather than hidden
- [x] Fixture-based API tests cover several comparables, a single comparable and none

## Comments

- Comparables are the `comparables` Source (`PyfundaComparablesSource`): `similar_listings()` ids, recently sold first then recently listed, one follow-up `listing()` fetch each, capped at `comparables_max_fetches` (default 5). A failed follow-up is left out but still counts against the cap. Resolving the Listing's globalId inside pyfunda may cost one extra provider call.
- Capture and Listing refetch skip it (`ON_REQUEST_SOURCES`, now in `app/wiring.py`); the user fetches it from the Dossier ("Vergelijkbare woningen ophalen") or the Brondekking, via the existing `POST /api/listings/{id}/sources/comparables/refetch`. TTL 14 days, labelled third-party.
- `metrics.asking_vs_comparables`: asking price per m² against the median price per m² of comparables with both price and living area; `coverage` is `not_fetched`, `none`, `thin` (fewer than `comparables_min_count`, default 3) or `sufficient`, always present. `comparables_value` = median per m² × living area. Comparison row gains `asking_vs_comparables_percent` (column now filled and sortable).
- Walk-away Maximum: the Verdict service sends `case.bid_limits` (affordable maximum; comparables maximum = value × (1 + `walk_away_comparables_premium`, default 0.10), only when coverage is sufficient) and rejects `walk_away_maximum_above_comparables`; affordability still wins. Bid Advice carries `comparables` (coverage, count, value, maximum) for the "hoe berekend" expander.
- Comparable prices are (last) asking prices, not registered sale prices; paid Kadaster data stays out of scope, so the spec's "comparables thin" risk remains partly open.
- Not done: no Flag for asking far above comparables (spec story 59); Flag rules are being touched by 11/12. The cap is not shown in the UI.
