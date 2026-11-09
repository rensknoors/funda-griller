# 29: Indexed WOZ, comparables by house type and a sourced Walk-away margin

**What to build:** The market half of ticket 28 (its design parts d and e). Two metrics still mislead the Oordeel: the asking price is compared with an unindexed WOZ value, and comparables are mixed across house types with a fixed weakly grounded margin. Index the WOZ to today, compare like with like, and make the margin a cited figure. Also carry VvE and erfpachtcanon into the monthly costs once the Case has them.

**Blocked by:** 28 (Accurate affordability and Oordeel inputs)

**Status:** ready-for-human (only the NHG 2027 primary-source check is left)

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

- [x] `ask_far_above_woz` reads the indexed WOZ; the Dossier shows raw and indexed WOZ with the index date
- [x] Comparables of another house type do not count towards coverage or the median
- [x] The weakly grounded Walk-away margin comes from config with a cited source, and the Biedadvies names it (per soort woning, at the user's request)
- [ ] The 2027 NHG limit in `config/affordability.toml` is checked against NHG's Voorwaarden en normen 2027 (now four consistent secondary sources: Geld.nl, Hypotheker, Banken.nl, Univé), and the SECONDARY mark dropped
- [x] From 2027 an NHG loan on a label E, F or G house includes a standard €20.000 for energy-saving measures, with an NHG limit of €530.000 for such loans (Banken.nl, Geld.nl); decide whether the affordable maximum and the Renovation Estimate should reflect it (decided: named in the Dossier, not counted)
- [x] Flag rule set version bumped
- [x] Verdict regression set re-run, changes explained in Comments

VvE and erfpachtcanon moved to ticket 32.

### Tests

Agreed seams: the HTTP API, plus the pure functions (indexing, WOZ dates, house type categories).

- [x] API: WOZ indexed from peildatum to today against a hand-computed example
- [x] API: an apartment comparable is left out for a detached house
- [x] API: Biedadvies derivation carries the margin source
- [x] Pure: WOZ dates in both notations, indexing to the latest published month, house type categories

## Comments

Done (2026-11-09). What changed and why:

- **WOZ in today's prices.** `config/price_index.toml` holds CBS 85773NED (national, monthly, 2020 = 100) from January 2019 to September 2026. The latest WOZ value is brought from the month of its peildatum to the latest published month: WOZ × index(now) / index(peildatum). `ask_far_above_woz` (rule version 2) reads the indexed value; the Dossier and the list show both. On the live Listing (WOZ 392.000, peildatum 2025-01-01) the ask goes from +51,8% to +41,6%.
- **WOZ dates.** Real stored runs date WOZ values as "1 jan 2025", not ISO as the fixtures did; the latest value was picked by string order. Dates are now parsed in both notations, so the latest value is chosen by date.
- **Woningtype.** The Listing and each comparable carry funda's object type and soort woning (`house_type`, also a Listing fact). Comparables of another kind (apartment vs house) never count; with at least `comparables_min_count` (now 5) of the same soort woning only those count. `comparables_max_fetches` went from 5 to 8, or five sufficient comparables would hardly ever be reached.
- **Margin per soort woning** (user's request: overbidding differs strongly by type). `config/bid_margins.toml`: NVM Marktoverzicht Nederland 2e kwartaal 2026, via openwoning.nl (SECONDARY; NVM's bijlage could not be fetched): tussenwoning 5,9%, appartement 5,6%, hoekwoning 4,4%, twee-onder-een-kap 3,5%, vrijstaand 0,6%, all homes 4,6%. NVM's 3rd quarter puts all homes at 3,3%, so these may run high; refresh when NVM's per-type figures for Q3 are found. The Case carries the margin, so a new table makes Verdicts Achterhaald. The live Listing's soort woning is unknown in the fixtures, so its weakly grounded Maximumbod goes from 624.750 (5%) to 622.370 (4,6%).
- **NHG E/F/G.** `nhg_energy_measures` names the standard €20.000 (2027) when the label is E, F or G and the loan stays under €530.000; the figures leave it out, as agreed.
- **Verdict prompt version 6:** names the indexed WOZ, the type-matched comparables and the margin source.
- **Not done:** the 2027 NHG limit is still SECONDARY (NHG's V&N 2027 not readable); the regression set was not re-run (paid; prompt and flag rules changed, so tiers may move). Run `uv run python -m app.verdict_regression run --yes` in `backend/`.

Code review (2026-11-09) found, and fixed before commit:

- A WOZ value whose peildatum falls outside the index series silenced `ask_far_above_woz`; the rule (version 3) now falls back to the raw WOZ value. Source facts are ordered by their parsed date, so "1 jan 2025" style dates sort right.
- The Case's `asking_price_margin` carries `provenance: rule` and `computed_at`, as rule values must (CODING_STANDARDS.md, Evidence).
- The NHG energy amount is named only when the loan actually goes with NHG.
- Comparables of unknown type keep counting (benefit of the doubt); a test now pins that choice.
- Left as judgement calls: Dutch house type labels exist in both backend and frontend; the "indexed, else raw" WOZ choice exists in the list and the Dossier; each new versioned table touches settings, loader, assembly, Case and Verdict staleness.

### Resultaat verdict regressie

```
{
  "run_at": "2026-11-09T21:55:26.301377+00:00",
  "model": "gemini-3.8-flash",
  "flag_rules_version": 13,
  "prompt_version": 6,
  "agreed": 4,
  "total": 6,
  "results": [
    {
      "name": "binnenhof-veldhoven",
      "expected": "consider",
      "actual": "consider",
      "outcome": "OK",
      "error": null,
      "deterministic": false
    },
    {
      "name": "buchterweg-holtum",
      "expected": "consider",
      "actual": "consider",
      "outcome": "OK",
      "error": null,
      "deterministic": false
    },
    {
      "name": "example-asking-far-above-woz",
      "expected": "skip",
      "actual": "consider",
      "outcome": "DIFF",
      "error": null,
      "deterministic": false
    },
    {
      "name": "example-efficient-family-home",
      "expected": "consider",
      "actual": "consider",
      "outcome": "OK",
      "error": null,
      "deterministic": false
    },
    {
      "name": "example-flood-depth-high",
      "expected": "skip",
      "actual": "consider",
      "outcome": "DIFF",
      "error": null,
      "deterministic": false
    },
    {
      "name": "example-label-deal-breaker",
      "expected": "hard_no",
      "actual": "hard_no",
      "outcome": "OK",
      "error": null,
      "deterministic": true
    }
  ]
}
```

Regression run analysed (2026-11-09, prompt version 6, Flag rule set 13):

- **Tiers: unchanged.** 4/6 agree, the same entries as both runs before this ticket. The two DIFFs (`example-asking-far-above-woz`, `example-flood-depth-high`) are placeholder entries with guessed tiers and differed the same way before tickets 28 and 29.
- **Maximumbod.** This was derived without the model, with the code before this ticket (d946958) and after it.
  - Lower for 2 of 5: `example-efficient-family-home` goes from €551.250 to €549.150, and `example-flood-depth-high` from €472.500 to €470.700. Both rest on the asking price, and the margin goes from 5% to 4,6% (soort woning unknown).
  - Unchanged for the other 3. Two rest on sufficient comparables. The third, `example-asking-far-above-woz`, is bound by affordability.
- **WOZ Signaal.** Nothing changes for any entry. Every entry that raised `ask_far_above_woz` still does with the indexed WOZ, and the indexed percentages are a few points lower.
- **Comparables.** The two real entries were frozen before the soort woning was captured. Their comparables are therefore not filtered by type, and the type filter is not exercised by the set yet. Re-adding them after a fresh capture would cover it.
