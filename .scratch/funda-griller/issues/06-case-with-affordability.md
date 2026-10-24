# 06: Case with affordability

**What to build:** A Case detail screen for a Listing, assembled deterministically from the latest Listing snapshot and the current Buyer Profile. It shows Listing facts with provenance, and the computed affordability: maximum mortgage, kosten koper, equity from the current home, monthly cost at the asking price, and headroom above the ask. The rule year behind the numbers is displayed. The Case contains no judgement.

**Blocked by:** 04 (Capture a Listing by URL), 05 (Buyer Profile)

**Status:** resolved

- [x] Opening a Listing shows its Case: Listing facts, each labelled with provenance
- [x] Maximum mortgage, kosten koper, equity, monthly cost at asking price and bidding headroom are computed from the profile and the Listing
- [x] Affordability is driven by a data table per year; the year used is shown on the Case
- [x] The energielabel's effect on borrowing capacity is included
- [x] The Case is rebuilt when the profile or snapshot changes and records which versions produced it
- [x] The Case builder does no I/O and no judgement; an import-linter contract in the backend config forbids it from importing adapters, storage, settings or the LLM client
- [x] API tests with fixture profiles cover typical, low-income and high-equity households
- [x] The Case detail screen is built to the design brief

## Notes

- Case is built on read from the latest snapshot and latest profile (`GET /api/listings/{id}/case`); nothing is stored, so it is never out of date. `built_from` records snapshot id and profile version.
- Rules: `config/affordability.toml`, one `[years.N]` table; the loader picks the current year or the latest earlier one, and the Case reports `rules.year` / `is_current_year`.
- **The 2026 figures (housing ratios, test rate, energielabel bonuses, starter limit, fixed costs) are modelling assumptions, not verified against Nibud/Rijksoverheid.** Verify before relying on them.
- The Case exposes derived figures only (no income or balances), since it later reaches the LLM.
- Dossier screen built: header, Betaalruimte, Kenmerken on the four-track grid with ADV stamps, rules year. Deferred to the tickets that bring the data: Brondekking bar, Signalen, group index/filters, stamp Popover, Documenten, Prijsverloop, header tier mark and WOZ/comparable deltas (07, 08, 09, 14, 18).
