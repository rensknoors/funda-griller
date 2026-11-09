# 29: Indexed WOZ, comparables by house type and a sourced Walk-away margin

**What to build:** The market half of ticket 28 (its design parts d and e). Two metrics still mislead the Oordeel: the asking price is compared with an unindexed WOZ value, and comparables are mixed across house types with a fixed weakly grounded margin. Index the WOZ to today, compare like with like, and make the margin a cited figure. Also carry VvE and erfpachtcanon into the monthly costs once the Case has them.

**Blocked by:** 28 (Accurate affordability and Oordeel inputs)

**Status:** needs-triage

### Current state

- `ask_far_above_woz` (`config/flag_rules.toml`, threshold 1.15) compares the asking price with the raw WOZ value (`_asking_vs_woz`, `backend/app/case.py`). WOZ 2026 has peildatum 2025-01-01; after years of price growth +15% is ordinary, so the Flag fires on most houses.
- Comparables (`_asking_vs_comparables`, `backend/app/case.py`) are asking prices of recently sold houses; the per-m² median ignores house type, and 3 count as sufficient (`comparables_min_count`).
- With thin comparables the Walk-away Maximum is asking + 5% (`walk_away_asking_price_margin`, `backend/app/settings.py`), with no source for the figure.
- Monthly costs (ticket 28) are net of hypotheekrenteaftrek but leave out VvE bijdrage and erfpachtcanon: the Case holds neither as a fact.

### Design

- **WOZ:** a versioned table of the CBS/Kadaster price index for existing owner-occupied homes (CBS StatLine 85773NED or its successor; regional where available, national otherwise), by month. `asking_vs_woz` reports raw and indexed (WOZ × index(now) / index(peildatum)); the Flag reads the indexed one. Fetching the series needs network access the sandbox lacks: fetch by hand or through a Source.
- **Comparables:** keep only comparables of the same house type (apartment or not, at least) when enough remain; raise `comparables_min_count` to 5.
- **Margin:** `walk_away_asking_price_margin` gets a source and date in config (e.g. the share sold above asking and the average overbid, by region if a public figure exists). The Biedadvies names the margin and its source.
- **VvE and erfpacht:** read VvE bijdrage from the Listing and erfpachtcanon from Findings into the Case; show them as separate monthly lines next to the net mortgage cost.

### Acceptance criteria

- [ ] `ask_far_above_woz` reads the indexed WOZ; the Dossier shows raw and indexed WOZ with the index date
- [ ] Comparables of another house type do not count towards coverage or the median
- [ ] The weakly grounded Walk-away margin comes from config with a cited source, and the Biedadvies names it
- [ ] VvE and erfpachtcanon, when known, show beside the net monthly cost in the Dossier and the export
- [ ] Flag rule set version bumped; Verdict regression set re-run, changes explained in Comments

### Tests

- [ ] API: WOZ indexed from peildatum to today against a hand-computed example
- [ ] API: an apartment comparable is left out for a detached house
- [ ] API: Biedadvies derivation carries the margin source
