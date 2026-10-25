# 19: Commute Flag

**What to build:** The Buyer Profile's commute destinations (label, address, `max_minutes`) are considered in Flags, so "too far" means what it means for this household (spec stories 4 and 57). A new Source computes the travel time from the Listing's coordinates to each destination address, and a Flag rule raises a con when a destination is further than its `max_minutes`.

**Blocked by:** 07 (Energielabel and WOZ Sources), 08 (Flags and deterministic Hard no)

**Status:** ready-for-agent

- [ ] Commute destination addresses are geocoded once, locally cached, through a new port with a fixture-backed fake; the address never reaches the Verdict model (only label and minutes do, as today)
- [ ] A `commute` Source returns travel minutes per destination (mode stated, e.g. by car or public transport) from the Listing's latitude and longitude, with a fetch date and TTL; no coordinates or no destinations means skipped, not failed
- [ ] A Flag rule raises one con per destination over its `max_minutes`, citing the travel time and the threshold; a deal-breaker naming the commute (e.g. "te ver van werk") is hit by it
- [ ] The Case's Brondekking shows the commute Source like the others; Stale after its TTL
- [ ] Fixture-based API tests cover within limit, over limit, no coordinates, and the routing service failing while the Case still builds

## Comments

- Found by the code review of `integration/funda-griller` (2026-10-25): no ticket 07 to 18 covered commute in Flags.
- Needs an outside geocoding and routing service (e.g. PDOK Locatieserver for geocoding; a routing API for travel time), so it is a new port and Source client per CODING_STANDARDS Boundaries. Pick the services and check their terms at build time; the Buyer Profile addresses are private (spec Privacy rules), so prefer a service that needs no account and keeps no logs, or run the geocoding via PDOK, which is a government service.
- Open: which travel mode(s) to compute, and whether `max_minutes` means door-to-door at rush hour.
