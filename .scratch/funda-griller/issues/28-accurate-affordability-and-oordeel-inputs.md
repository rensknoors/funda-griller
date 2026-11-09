# 28: Accurate affordability and Oordeel inputs (2026/2027 rules)

**What to build:** The Oordeel rests on affordability figures and market metrics that are partly out of date, partly never verified, and partly computed wrong. Bring the rule tables up to the official 2026 figures, add a 2027 table, fix the arithmetic that lets a household finance what a lender never would, and stop two market metrics from misleading the model. Decision support, not advice: every figure cites its source and check date in `config/affordability.toml`.

**Blocked by:** none

**Status:** resolved

### Current state

Review of `backend/app/affordability.py`, `backend/app/verdict.py`, `backend/app/case.py` and `config/*.toml`, against public sources checked 2026-11-09.

**Out-of-date or unverified figures (`config/affordability.toml`)**

- `housing_ratio` runs 20–35%. The Nibud financieringslast table for 2026 (via Hypotheker) runs about 19.3–26.5% (€80k: ~24.2%). The file's own header already marks it UNVERIFIED.
- `test_rate = 0.05` is applied to every mortgage (`_max_mortgage`, `affordability.py:88`). The AFM toetsrente (5% through Q3 2026) applies only to a rentevaste periode shorter than 10 years; for 10 years or longer the lender tests at the actual rate (10 jaar vast on 2026-11-02: ~4.40% with NHG, ~4.78% without).
- The two errors partly cancel. Rough check, single, €80k, 10 jaar vast without NHG: code ~€372k, Nibud norm ~€325k (incl. alleenstaandenbonus). About 15% too high; the exact gap depends on the official table.
- `mortgage_rate = 0.04` for monthly costs (`affordability.py:149`), against ~4.4–4.8% in the market: about €185/month low on €400k.
- Missing norms: alleenstaandenbonus (€17k in 2026, €18k in 2027); student debt and other loans lowering capacity; NHG kostengrens (€470k in 2026, €500k in 2027) with its lower rate and 0.4% borgtochtprovisie in kosten koper.
- No 2027 table. `load_rules(..., now.year)` (`assembly.py:34`, `:50`) picks rules by today, while the startersvrijstelling (and the price limit) depends on the date of levering, typically months after a bid. A bid in November 2026 usually transfers in 2027: starter limit €555k → €615k (Belastingplan 2027, not yet final), NHG €500k, Nibud 2027 norms (~€10k more at equal income), energy label bonus unchanged.

**Arithmetic errors**

- **Kosten koper are financed.** `_budget` (`affordability.py:99`) adds max mortgage, equity and own funds into one pot and divides by `1 + transfer_tax_rate`. A mortgage may not exceed 100% of the market value, so kosten koper (and the Direct nodig renovation, outside a bouwdepot) must come from equity and own funds. A household without savings gets an affordable maximum no lender would finance. `mortgage_needed` in `compute` has the same gap.
- **Startersvrijstelling is all-or-nothing.** `_is_starter` (`affordability.py:83`) exempts only when every adult is 18–34. The exemption is per buyer for their share: a couple of 30 and 36 pays 2% on half. Age counts at levering, not today. It can be used once in a lifetime; the profile cannot say whether it has been.
- **Monthly cost is gross only.** No hypotheekrenteaftrek (2026 max rate ~37.6%), no eigenwoningforfait, no VvE bijdrage or erfpachtcanon when known.

**Misleading market metrics**

- `ask_far_above_woz` (`config/flag_rules.toml:51`, threshold 1.15) compares the asking price with an unindexed WOZ value. WOZ 2026 has peildatum 2025-01-01; after years of price growth, +15% is ordinary, so the Flag fires on most houses and tells the model nothing.
- Comparables (`case.py:227`) are asking prices of recently sold houses, while sale prices run some percent above asking. The per-m² median ignores house type, and 3 count as sufficient.
- With thin comparables the Walk-away Maximum is asking + 5% (`settings.py:69`), less Direct nodig. In a market that overbids, that sits below what such houses go for, so the Biedadvies loses structurally without saying why.

### Design

- **Rule tables (per year, `config/affordability.toml`):**
  - Woonquote as the official Nibud table by toetsinkomen (and by rate band if the official table has one), 0.1-point steps.
  - `toetsrente` (AFM, for < 10 years fixed) and a `market_rate` per NHG / non-NHG for ≥ 10 years fixed, both dated.
  - `single_household_bonus`, `nhg_limit`, `nhg_fee_rate`, `max_ltv = 1.00`.
  - A 2027 table, its not-yet-final figures marked as such in the header comment.
  - Every figure verified against a primary source (Nibud advice in Kamerstuk 2026D54667, AFM, nhg.nl, Belastingdienst) and listed in the header with check date. A third-party table is not enough.
- **Buyer Profile (finances):**
  - `fixed_rate_years` (default 10)
  - `other_monthly_debt` (student debt per DUO monthly amount and other loans; how it weighs per Nibud norm)
  - per adult: `starter_exemption_used`
  - Shown in the Gevolgen panel; none of it reaches the LLM (`reduce_profile` unchanged).
- **Rules year by expected levering:** pick the table for an expected levering date (today + a configured offset, default 3 months), not today. The Case records the year used; `rules.is_current_year` becomes "rules match the expected levering year".
- **Affordability arithmetic:**
  - Max mortgage = `min(income-based norm, max_ltv × price)`. Kosten koper and the Direct nodig midpoint come from equity + own funds. The affordable maximum is the highest price where both hold.
  - Transfer tax per adult share, age at expected levering, with the once-in-a-lifetime flag.
  - NHG: when the mortgage fits under the limit, the NHG rate and the 0.4% fee apply.
  - Monthly cost: gross and net (aftrek at the 2026/2027 maximum rate, eigenwoningforfait), plus VvE and erfpachtcanon as separate lines when the Case has them. The Oordeel shows net; gross stays visible.
- **WOZ:** index the WOZ value from its peildatum to today with the CBS/Kadaster price index for owner-occupied homes (regional when available; national otherwise), stored in a versioned table. `asking_vs_woz` reports both raw and indexed; the Flag reads the indexed one.
- **Comparables and Walk-away Maximum:**
  - Prefer comparables of the same house type. Raise `comparables_min_count` to 5.
  - The weakly grounded margin becomes configurable per region, defaulting to a documented overbidding figure (source and date in config). The Biedadvies states the margin and its source.
- **Prompt:** bump `VERDICT_PROMPT_VERSION`; tell the model the monthly cost is net and which rules year applies.
- Bump the rule table, Flag rule set and cost table versions so existing Oordelen show **Achterhaald**.

### Acceptance criteria

- [x] `affordability.toml` has verified 2026 and 2027 tables; no figure in the header is UNVERIFIED, each cites a primary source and check date. Exception: the 2027 NHG limit (€500.000) rests on four consistent secondary sources, marked SECONDARY; checking it against NHG's Voorwaarden en normen 2027 moved to ticket 29.
- [x] Max mortgage tests at the toetsrente for < 10 years fixed and at the market rate for ≥ 10 years
- [x] A single adult gets the alleenstaandenbonus; other monthly debt lowers the max mortgage
- [x] A household with €0 own funds and €0 equity gets an affordable maximum of €0 (kosten koper cannot be financed)
- [x] Mortgage needed never exceeds `max_ltv × price` (the rest shows as `own_funds_shortfall`)
- [x] A couple aged 30 and 36 pays transfer tax on half the price; an adult who used the exemption before pays on their share
- [x] Rules are chosen by expected levering date; a November 2026 Case uses the 2027 table
- [x] NHG rate and fee apply when the mortgage fits under the year's limit
- [x] The Oordeel and Markdown export show net monthly cost, with gross beside it
- [x] Verdict regression set re-run; changes in tier or Maximumbod explained in Comments
- [x] `GLOSSARY.md` updated where terms change (Walk-away Maximum, affordable maximum)

Moved to ticket 29: indexed WOZ, comparables by house type, a sourced Walk-away margin, and VvE/erfpachtcanon in the monthly costs.

### Tests

Agreed seam: the HTTP API (as the existing tests), not the pure functions.

- [x] API: max mortgage at €70k and €100k, couple and single, 5 and 10 years fixed, against the Nibud worked examples (advies 2027 tabel 3 and 4)
- [x] API: affordable maximum with zero own funds, with €30.000 saved, and with a Direct nodig midpoint
- [x] API: transfer tax for one starter, an exemption already used, at and €1 above the limit, and an adult turning 35 before levering
- [x] API: rules year follows the expected levering
- [x] API: net monthly cost and NHG fee against a hand-computed example
- [x] API: Buyer Profile accepts, validates and versions the new fields; Gevolgen figures change with them

## Comments

Raised from a review of the Oordeel on 2026-11-09. Sources consulted (consumer sites; verify against primary sources before entering figures):

- Hypotheker woonquote 2026: https://www.hypotheker.nl/media/3venb13y/woonquote_2026.pdf
- Toetsrente: https://www.hypotheker.nl/begrippenlijst/hypotheek-afsluiten/toetsrente-hypotheek/
- Rente november 2026: https://www.vanbruggen.nl/actueel/nieuws/2026/rust-op-de-rentemarkt-stilte-voor-de-storm
- Hypotheeknormen 2027: https://www.adfiz.nl/nieuws/hypotheeknormen-2027-meer-leenruimte-ook-zonder-loonstijging/ and https://www.tweedekamer.nl/downloads/document?id=2026D54667
- NHG 2026/2027: https://banken.nl/nieuws/26557/nhg-grens-stijgt-naar-470000 and https://www.geld.nl/hypotheek/expert/nieuws/nhg-grens-stijgt-in-2027-naar-500000
- Startersvrijstelling 2027: https://www.hypotheker.nl/actueel/nieuwsberichten/2026/prinsjesdag-2026-wat-verandert-er-voor-huizenkopers-in-2027/

Large ticket. If it goes to an agent, split along the Design headings: (a) rule tables + rules year, (b) affordability arithmetic + profile fields, (c) net monthly cost, (d) WOZ indexing, (e) comparables and Walk-away margin.

Done (parts a–c, 2026-11-09). What changed and why:

- **Norms from the regeling itself.** The financieringslast tables for 2026 (wetten.overheid.nl, Trhk as of 2026-01-01) and 2027 (Wijzigingsregeling hypothecair krediet 2027, Stcrt. 2026, 38415, published 2026-11-02) are in `config/affordability.toml` as income × toetsrente grids. Both reproduce the Nibud worked examples (advies 2027 tabel 3 and 4) to the euro, once the mortgage is rounded to the nearest euro as Nibud does (the old code floored). The Hypotheker table cited above turned out to be one rate column (3,001–3,500%) of the 2026 grid.
- **Toetsrente vs offered rate.** Under ten years fixed: the AFM 5% (or the offered rate when higher). Ten years or longer: the offered rate, with NHG (4,40%) or without (4,78%), Van Bruggen index 2026-11-02. The NHG route is capped at the NHG limit; the larger of the two routes is the maximum mortgage.
- **What moved most.** The typical household (€95k, label B) goes from €496.660 to €443.174 maximum mortgage, and its affordable maximum for the live Listing from €704.519 to €650.351: the old ratios (30–35%) were too high and kosten koper were being borrowed. A household with no savings now has a budget of €0, since kosten koper cannot be borrowed.
- **Starters.** The exemption is now per buyer for their share, aged 18–34 at levering, unless they used it before; 2027 limit €615.000 (Belastingplan 2027, not yet law).
- **Net monthly costs.** First-year net = gross annuity less 38,16% (2027 estimate) of interest above 0,35% eigenwoningforfait over the asking price. Wet Hillen is not modelled (only matters when the forfait exceeds the interest).
- **Not modelled (still):** AOW-age tables, the extra mortgage for energy-saving measures (Trhk art. 4 lid 4), a bouwdepot for renovation (the Direct nodig midpoint must come from own funds), VvE and erfpachtcanon (ticket 29).
- **Walk-away tests.** With lower affordability, the typical household's affordability now binds the Maximumbod against sufficient comparables. Tests about a comparables-bound Maximumbod use a new `well_off_profile` (€100k saved) so they keep testing that path.
- **e2e** use the real clock, so their expected figures assume a levering in 2027; they will shift once a 2028 table is added.
- **Regression set not run:** it calls the paid Verdict model (6 calls). Run `uv run python -m app.verdict_regression run --yes` in `backend/` and record the outcome here.
- - Results:
- - {
    "run_at": "2026-11-09T21:13:17.771614+00:00",
    "model": "gemini-3.8-flash",
    "flag_rules_version": 11,
    "prompt_version": 5,
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

Code review (2026-11-09) found, and fixed before commit:

- The NHG fee broke the binary search: a price whose NHG fee tipped own funds over was judged unfinanceable even when a loan without NHG worked, so the budget could drop by a large step for €1.000 less savings. Loans with and without NHG are now separate routes; each only gets harder as the price rises, so their union does too.
- `mortgage_needed` could exceed the price; it now stops at `max_ltv × price` and the rest is `own_funds_shortfall`, which the Dossier names.
- The rule table has a `version`; a change marks Verdicts Achterhaald even within the same year. Verdicts made before this change carry no rule table version and show as Achterhaald.
- "Achterhaald" no longer labels "no norms yet for the levering year" (it means an out-of-date Verdict or Case); that note reads "Let op".

Regression run (2026-11-09, prompt version 5), analysed:

- **Tiers: no change from this ticket.** 4/6 agree. The two DIFFs (`example-asking-far-above-woz` and `example-flood-depth-high`, expected skip, got consider) came out the same in both earlier runs on 2026-10-26 (prompt version 4, before this ticket). They are placeholder entries with guessed tiers (see `config/verdict_regression/README.md`), so they say more about the guesses than about the model.
- **Maximumbod.** The harness records tiers only, so the Walk-away Maximum was derived for each entry with the code before (4e93821) and after this ticket. It is deterministic, so no model calls were needed.
  - Unchanged for 3 of 5: `buchterweg-holtum`, `example-efficient-family-home` and `example-flood-depth-high`, whose basis (comparables or asking price) stays below what the household can afford.
  - Lower for 2 of 5, where affordability now binds instead of the basis. `binnenhof-veldhoven` comes out about 2% lower (real entry, so amounts stay out of this public file). `example-asking-far-above-woz` goes from €672.000 to €645.469.
  - The cause in both cases is the lower affordable maximum (official woonquote, kosten koper from own funds).
