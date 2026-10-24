# 08: Flags and deterministic Hard no

**What to build:** Declarative, versioned Flag rules produce pros, cons and risks in the Case, each citing its rule and the facts behind it, grouped on the Case detail screen. If the Case hits a deal-breaker from the Buyer Profile, the result is a deterministic Hard no with the reason displayed. Starts with a small set of rules; the structure makes adding more a data change.

**Blocked by:** 06 (Case with affordability)

**Status:** ready-for-agent

- [ ] Rules are declarative and versioned; a Flag records rule id, rule version and evidence facts
- [ ] A starter set covers at least: poor energielabel versus tolerance, ask far above WOZ, ask beyond affordability headroom, and a missing must-have
- [ ] Thresholds can depend on derived Buyer Profile values
- [ ] Flags appear on the Case detail grouped as pro, con and risk, each expandable to rule and evidence
- [ ] A deal-breaker hit sets the tier to Hard no deterministically and displays which deal-breaker caused it
- [ ] Changing the profile or the rules produces a new Case version
- [ ] API tests cover each starter rule and a deal-breaker forcing Hard no
