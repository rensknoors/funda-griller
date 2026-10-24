# 07: Energielabel and WOZ Sources

**What to build:** The Source port, with the first two Sources feeding the Case: energielabel from the official register, and WOZ history from the Listing provider's third-party price-history data, clearly labelled as unofficial. Each Source fact carries its fetch date. Facts older than their time-to-live show as Stale. Refetching is manual. A failing Source never fails the Case.

**Blocked by:** 06 (Case with affordability)

**Status:** ready-for-agent

- [ ] The Case shows the official energielabel and flags a mismatch with the Listing's claim as a fact (not a judgement)
- [ ] WOZ values over time appear in the Case, labelled third-party
- [ ] Asking price versus latest WOZ is a computed metric in the Case
- [ ] Every Source fact shows its fetch date; Staleness is computed from a per-Source time-to-live
- [ ] A manual refetch action exists per Listing and per Source; nothing refreshes automatically
- [ ] Stale facts remain visible with a Stale badge, per the design brief
- [ ] One Source failing leaves the Case intact, and the Case lists Sources as succeeded, failed or skipped
- [ ] API tests use fixtures and a controllable clock to cover Stale marking and Source failure
