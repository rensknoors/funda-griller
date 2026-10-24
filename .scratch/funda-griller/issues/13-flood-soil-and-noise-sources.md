# 13: Flood, soil and noise Sources

**What to build:** Two more Sources feed the Case: flood and soil risk for the address, and noise levels. They follow the same fetch-date, Stale and manual-refetch behaviour as the first Sources, and trigger Flags where they cross thresholds.

**Blocked by:** 07 (Energielabel and WOZ Sources)

**Status:** ready-for-agent

- [ ] Flood and soil risk facts appear in the Case for a Listing's coordinates
- [ ] Noise levels appear in the Case
- [ ] Both carry fetch dates, respect time-to-live and refetch manually
- [ ] At least one Flag rule per Source raises a risk or con above a threshold
- [ ] A failing or unavailable Source degrades gracefully as in ticket 07
- [ ] Fixture-based API tests cover each Source and its Flag
