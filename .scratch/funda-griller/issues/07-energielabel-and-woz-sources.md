# 07: Energielabel and WOZ Sources

**What to build:** The Source port, with the first two Sources feeding the Case: energielabel from the official register, and WOZ history from the Listing provider's third-party price-history data, clearly labelled as unofficial. Each Source fact carries its fetch date. Facts older than their time-to-live show as Stale. Refetching is manual. A failing Source never fails the Case.

**Blocked by:** 06 (Case with affordability)

**Status:** resolved

- [x] The Case shows the official energielabel and flags a mismatch with the Listing's claim as a fact (not a judgement)
- [x] WOZ values over time appear in the Case, labelled third-party
- [x] Asking price versus latest WOZ is a computed metric in the Case
- [x] Every Source fact shows its fetch date; Staleness is computed from a per-Source time-to-live
- [x] A manual refetch action exists per Listing and per Source; nothing refreshes automatically
- [x] Stale facts remain visible with a Stale badge, per the design brief
- [x] One Source failing leaves the Case intact, and the Case lists Sources as succeeded, failed or skipped
- [x] API tests use fixtures and a controllable clock to cover Stale marking and Source failure

## Notes

- Sources run on capture and on Listing refetch (`POST /api/listings/{id}/refetch`); one Source alone via `POST /api/listings/{id}/sources/{source}/refetch`, which returns the rebuilt Case. Reading a Case never fetches.
- Every run is stored (`source_runs`); the Case shows facts from the latest succeeded run, so a failed refetch keeps the last good facts (still Stale) and reports the Source as failed. Sources configured but never run show as skipped (`not_fetched`).
- Staleness is computed on read from the run time and `source_ttl_days` (stale when older than the TTL); `create_app` takes a clock, the tests use a `FakeClock` fixture.
- Source trust (official vs third-party) is fixed in the Case builder: energielabel official, WOZ and unknown Sources third-party.
- The register energielabel, when present, replaces the Listing claim in the affordability bonus. The mismatch is `metrics.energy_label_check` (no Flag; Flags are ticket 08). `metrics.asking_vs_woz` uses the WOZ value with the latest `as_of`.
- Production: energielabel from RVO EP-Online v5 `PandEnergielabel/Adres` (query and response shape checked against its swagger on 2026-10-24; needs `FG_EP_ONLINE_API_KEY`, otherwise skipped). The Listing provider now captures postcode and house number for it. WOZ from pyfunda `price_history()` (Walter Living), changes with status `woz`. Neither adapter has been run against the live service; the WOZ `date` format in live data is unverified.
- Deferred: `3 verouderd` count on the Listings list (15/18), stamp Popover with URL and TTL (18; TTL is in a title tooltip for now), group index and filters (18).
