# 15: Listings comparison view

**What to build:** The Listings list becomes the comparison view: sortable and filterable by Verdict tier and price, with key metrics side by side, Stale indicators, archive, and a visible status change after a refetch.

**Blocked by:** 07 (Energielabel and WOZ Sources)

**Status:** resolved

- [x] The list shows tier, price, area and key metrics per Listing
- [x] Sort and filter by tier and price work
- [x] Listings with Stale data are identifiable at a glance
- [x] A Listing can be archived and restored without losing history
- [x] After a refetch, a change of Listing status (for example available to sold) is visible
- [x] The view follows the design brief

## Comments

- Price, area and key metrics are shown, and so is the tier for a deal-breaker Hard no. The other three tiers have to wait for Verdicts (09), so the first criterion stays open. Until then every other Listing shows "Nog geen oordeel".
- Each Listing from `GET /api/listings` (and from capture, refetch, archive and restore) now carries `archived` and a `comparison` row built by `app/comparison.py` (pure, under the Case-builder import contract): `tier`, `hard_no_reason`, `status`, `status_change` (`{from, to}` against the previous snapshot), `asking_price`, `previous_asking_price` (set only when it changed), areas, `energy_label` (`{value, official}`, register first), `asking_vs_woz_percent`, `headroom`, `flag_counts`, `stale_count` (Stale Source facts) and `last_fetched_at`.
- **For 09:** `main.with_comparison` calls `summarise(snapshots, case)`. Pass the latest Verdict's tier as `summarise(..., tier=...)` using `must_buy | consider | skip | hard_no`. A Case Hard no always overrides it. The frontend already renders and filters all four tiers plus `null` (`frontend/src/comparison.ts`). Also add "Oordeel opnieuw draaien" to the row menu in `ListingsTable.tsx`.
- Sort order for tiers: Zeker kopen, Overwegen, Nog geen oordeel, Overslaan, Harde afwijzing. An unrated Woning still needs attention, so it sits above Overslaan. Rows with the same tier sort by price ascending, and missing values sort last. Sorting and filtering run client-side. `GET /api/listings` hides archived Listings unless `include_archived=true` (the view always asks for them and shows "N gearchiveerd" as a link).
- Archive and restore append to `listing_archive_events`. Snapshots, Source runs and the Case stay intact. Archiving asks for confirmation in a Base UI Dialog. The row menu (Base UI Menu) has Opnieuw ophalen and Archiveren/Terugzetten. Arrow keys move between rows, Enter opens the Dossier and `x` asks to archive.
- After a refetch the row flashes for 200 ms (none under reduced motion). A sold Listing shows its address struck through and a "Verkocht" chip, with "was Beschikbaar" next to it. A price change shows ▲/▼ next to the price.
- Not done: the "t.o.v. vergelijkbaar" column shows "–" until comparables arrive (14). Duplicate-URL notice and "laden" skeleton rows per newly pasted URL are unchanged from 04.
- Playwright: `e2e/comparison.spec.ts`. The e2e fake provider serves `Markt 3` as available first and sold on refetch. The Stale case stubs `stale_count` through `page.route`, because the e2e backend runs on a real clock.
- Closed with 09: `with_comparison` passes the latest Verdict tier into `summarise` (a Case Hard no still overrides it), and the row menu has Oordeel opnieuw draaien, which makes a new Verdict version and refreshes the list. API tests in `backend/tests/test_verdict_api.py`; Playwright in `e2e/verdict.spec.ts`.
