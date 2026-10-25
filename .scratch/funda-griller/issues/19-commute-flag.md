# 19: Commute Flag

**What to build:** The Buyer Profile's commute destinations (label, address, `max_minutes`) are considered in Flags, so "too far" means what it means for this household (spec stories 4 and 57). A new Source computes the travel time from the Listing's coordinates to each destination address, and a Flag rule raises a con when a destination is further than its `max_minutes`.

**Blocked by:** 07 (Energielabel and WOZ Sources), 08 (Flags and deterministic Hard no)

**Status:** resolved

- [x] Commute destination addresses are geocoded once, locally cached, through a new port with a fixture-backed fake; the address never reaches the Verdict model (only label and minutes do, as today)
- [x] A `commute` Source returns travel minutes per destination (mode stated, e.g. by car or public transport) from the Listing's latitude and longitude, with a fetch date and TTL; no coordinates or no destinations means skipped, not failed
- [x] A Flag rule raises one con per destination over its `max_minutes`, citing the travel time and the threshold; a deal-breaker naming the commute (e.g. "te ver van werk") is hit by it
- [x] The Case's Brondekking shows the commute Source like the others; Stale after its TTL
- [x] Fixture-based API tests cover within limit, over limit, no coordinates, and the routing service failing while the Case still builds

## Comments

- Found by the code review of `integration/funda-griller` (2026-10-25): no ticket 07 to 18 covered commute in Flags.
- Needs an outside geocoding and routing service (e.g. PDOK Locatieserver for geocoding; a routing API for travel time), so it is a new port and Source client per CODING_STANDARDS Boundaries. Pick the services and check their terms at build time; the Buyer Profile addresses are private (spec Privacy rules), so prefer a service that needs no account and keeps no logs, or run the geocoding via PDOK, which is a government service.
- Open: which travel mode(s) to compute, and whether `max_minutes` means door-to-door at rush hour.
- User decisions (2026-10-25):
  - Routing: OpenRouteService, API key from configuration (`FG_OPENROUTESERVICE_API_KEY`, in `.env.example`); no key means the commute Source is skipped.
  - Geocoding: PDOK Locatieserver (government, no account), so the private destination address goes only to PDOK; only coordinates go to OpenRouteService. Geocodes are cached locally.
  - Mode: ORS has no public transport. Car (`driving-car`) and bike (`cycling-regular`) are computed; a destination is over its limit when the faster mode exceeds `max_minutes`. The Case fact and the Flag evidence state the modes and that public transport is not included. `max_minutes` is compared with ORS's free-flow travel time, not rush hour.
- Built (2026-10-25): ports `Geocoder` and `TravelTimeRouter` (`app/ports.py`) with `PdokGeocoder` and `OpenRouteServiceRouter` (`app/source_clients.py`, matrix API, one request per mode for all destinations) and fakes in `tests/fakes.py`; `CommuteSource` (`app/commute.py`) reads the latest Buyer Profile's destinations and caches geocodes in the `geocodes` table. Fact `commute.travel_minutes` per destination: `{destination, minutes, mode, minutes_by_mode, public_transport: false}`, trust third-party, TTL 180 days. Rule `commute_too_long` (kind `over_max_minutes`, aliases include "te ver" and "reistijd"); Flag rule set version 8. Dossier shows a Reistijd group with ORS/OSM attribution.
- Terms checked at build time: ORS Standard plan is free, 500 matrix requests a day and 40 a minute, attribution required, no commercial use (openrouteservice.org/plans, terms of service); the key goes in the `Authorization` header. PDOK Locatieserver v3.1 `free` needs no key.
- Deferred: commute facts are matched to destinations by label, so changing a destination's address (same label) or adding a destination needs a refetch of the commute Source (Opnieuw ophalen) to take effect; nothing refetches automatically on a Buyer Profile save.
