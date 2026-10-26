# 21: Renovation Estimate split by urgency

**What to build:** A **Renovation Estimate** (_Verbouwingsraming_) in the Case: what the house will cost to renovate, split into three urgency classes, **Direct nodig**, **Binnen 5 jaar** and **Optioneel**. Items are derived deterministically from Case facts by a versioned cost table (ADR-0001: the Case holds no judgement; the Verdict only cites the estimate). Each item has a low–high cost range, cites the facts that triggered it with their provenance, and is marked estimated. The Direct nodig midpoint lowers the house's affordable maximum and the Walk-away Maximum. Covers spec story 54's "likely renovation cost" of a poor energielabel.

**Blocked by:** 11 (Photos and Observations), 12 (Documents and Findings), 07 (Energielabel and WOZ Sources)

**Status:** resolved

### Cost table

- [x] New versioned TOML cost table, loaded like the Flag rules. Per item: `id`, Dutch label, urgency class, triggers, cost basis, low and high unit cost, `supersedes` list, `source` (e.g. Milieu Centraal, consumer price guide) and `price_year`. Table has a `version`
- [x] Seeded from public average prices; the user maintains the figures by hand
- [x] Cost basis is one of: fixed; per m² `living_area` (interior, insulation); size band on `living_area` (<80, 80–150, >150 m²) for roof and facade. A missing `living_area` uses the middle band and the item says so

### Triggers and items

- [x] Triggers read Observations (`observation.*`), Findings, Source facts (energielabel) and Listing facts (`construction_year`, `heating`), in the same condition vocabulary as the Flag rules
- [x] Build-year triggers (e.g. asbestos survey before 1994, foundation check before 1930, insulation before 1975 with no energielabel) produce inspection items (survey cost, not full repair), marked "op basis van bouwjaar"
- [x] One item per `id`: when several facts trigger it, it cites all of them and takes the most urgent class. An item in another item's `supersedes` list is dropped when that item is present (e.g. `renovation_needed: full` replaces kitchen, bathroom and cosmetic items)
- [x] Items without a trigger fact are left out, never guessed; the Case lists the missing inputs (no photos, no Vragenlijst, no energielabel)
- [x] The estimate is the same for every Buyer Profile: `renovation_tolerance` only steers the Verdict
- [x] The estimate is built for every Case, Hard no included

Starting triggers (seed, adjust while building):

- Direct nodig: damp or mould visible, roof poor, facade poor, seller-stated leaks/foundation/asbestos Findings, `renovation_needed: full`
- Binnen 5 jaar: kitchen or bathroom past a configured age, roof or facade fair, energielabel E–G (insulation, glazing), old boiler (cv-ketel) or wiring from the Vragenlijst
- Optioneel: `renovation_needed: cosmetic`, energy upgrades on label C–D (heat pump, solar)

### Effect on the numbers

- [x] Per class: low and high totals; the midpoint of Direct nodig is the figure used below
- [x] Affordable maximum for the house becomes `(available − Direct nodig midpoint) / (1 + transfer tax rate)`
- [x] Walk-away Maximum (ticket 20) becomes `min(that affordable maximum, (basis − Direct nodig midpoint) × (1 + margin))` for the comparables and asking-price bases; `WalkAwayDerivation` records the subtraction
- [x] Both subtractions show in the Bid Advice **Hoe berekend** expander
- [x] New con Flag rule `renovation_direct_high` when the Direct nodig midpoint exceeds a threshold in the Flag rules (default €25,000); deal-breaker aliases include "opknapper"

### Case, Verdict and UI

- [x] `built_from` records the cost table version, so a table change makes Verdicts Achterhaald
- [x] The Verdict prompt receives the classes, totals and items with provenance; `VERDICT_PROMPT_VERSION` is bumped and the regression set re-run against the real model (run 2026-10-26, see Comments)
- [x] Dossier group **Verbouwingskosten**: three classes, euro ranges, "geschat" stamps, evidence links as in Signalen, "prijspeil <year>", and the missing-inputs note
- [x] Comparison view (ticket 15) gets a **Direct nodig** column
- [x] GLOSSARY.md gets **Renovation Estimate** (_Dutch UI_: **Verbouwingsraming**; classes **Direct nodig**, **Binnen 5 jaar**, **Optioneel**); the Walk-away Maximum entry mentions the Direct nodig subtraction

### Tests

- [x] API tests: items from Observations, Findings, energielabel and build year; dedupe and `supersedes`; no photos or Documents (missing inputs listed); missing `living_area` (middle band); affordable maximum and Walk-away Maximum with and without Direct nodig items; `renovation_direct_high` Flag; cost-table version change marks a Verdict Achterhaald; Hard no still skips the LLM and still carries the estimate

## Notes

- Changes `verdict.derive_walk_away_maximum` from ticket 20. Ticket 20's code is done; only its real-model regression run is pending, which this ticket's re-run can cover.
- Bouwdepot (construction deposit) and the extra mortgage room for energy measures are out of scope.
- Built (2026-10-26): `config/renovation_costs.toml` (cost table, `version = 1`, seeded from Milieu Centraal and consumer price guides at `price_year` 2025; `size_bands`, `assumed_living_area` for per-m² items without a living area), loaded by `rules_loader.load_cost_table` from `Settings.renovation_costs_path`. `app/renovation.py` builds the estimate; triggers use the Flag rule conditions through the new `flags.holds` (plus a new `absent` kind, and `also` for extra conditions on one trigger). A trigger may set its own `urgency`; the most urgent wins.
- The Case carries `renovation_estimate` (items with `low`/`high`, `basis`, `size_assumed`, `inspection`, `source`, `price_year`, `estimated`, `evidence`; `classes` per urgency with `low`/`high`/`midpoint`; `direct_midpoint`; `missing_inputs` from `observations`, `vragenlijst` (an analysed Document other than the funda brochure) and `energielabel`). It is built from Case facts without the Buyer Profile, so it is the same for every profile, Hard no included. `built_from.cost_table_version` joins the `rules` input of a Verdict, so a table change marks Verdicts Achterhaald (older Verdicts without it read as changed too).
- `affordability.renovation_direct` and the affordable maximum (and so `headroom`) subtract the Direct nodig midpoint from the available funds; `WalkAwayDerivation.renovation_direct` records the subtraction from the comparables or asking-price basis. Both show in the Bid Advice "Hoe berekend" and the Dossier's Betaalruimte.
- New Finding topics `boiler_old` and `wiring_old` (extraction prompt says when they are present) trigger the cv-ketel and elektra items. Inspection items: foundation survey before 1930 (Direct nodig), asbestos survey before 1994 and energy advice before 1975 without any energielabel (Binnen 5 jaar); the repair items `supersedes` their survey. The seed has no `heating` trigger yet; triggers can read it.
- Flag rule `renovation_direct_high` (threshold 25,000, aliases "opknapper", "kluswoning"); Flag rules version 10. Comparison row `renovation_direct` and a sortable **Direct nodig** column. Dossier group **Verbouwingskosten** (`frontend/src/Verbouwingskosten.tsx`), reusing the Signalen evidence rows.
- `VERDICT_PROMPT_VERSION` is 4. Pending (box unticked): the regression set has not been re-run against the real Verdict model (costs money). Run `cd backend && uv run python -m app.verdict_regression run --yes`; it also covers ticket 20's pending re-run. Then tick the box and set `resolved`.
- Tests: `backend/tests/test_renovation_api.py` (test-owned cost table), `frontend/e2e/walk-away-renovation.spec.ts`.

## Comments

- Grilled (user, 2026-10-26): deterministic table over LLM estimate; Direct nodig midpoint subtracts from the basis of the Walk-away Maximum and from the available funds of the affordable maximum (a separate "cash needed" line would always fall short, because the affordable maximum already spends all own funds); `renovation_tolerance` steers the Verdict only; fixed 5-year horizon; ranges, not single figures; build-year triggers allowed as inspection items; prices from public averages with source and year; size bands for roof and facade; dedupe with `supersedes`; con Flag on a high Direct nodig total; estimate on every Case; Direct nodig column in the comparison view.
- Code review fixes (2026-10-26): `renovation_direct_high` title now names its threshold ("Veel Direct nodig onderhoud: meer dan € 25.000 (geschat)"; Flag rules version 11, rule meaning unchanged so rule version stays 1); UI copy uses **Direct nodig** in the Betaalruimte and Hoe berekend lines; the Vragenlijst missing-input check matches Documents of the user-added kind (`USER_DOCUMENT_KIND`, now shared in `app/findings.py` with `BROCHURE_KIND`) instead of "anything but the brochure" (there is no separate Vragenlijst kind); the `renovation.direct_midpoint` Flag input moved into `case._rule_inputs`; the size-band ternary became `renovation._size_band`, and an unknown cost `basis` raises at table load (`CostTable`). Status stays ready-for-human: the real-model regression re-run is still pending.
- Real-model regression run (user, 2026-10-26, `gemini-3.8-flash`, Flag rule set 11, prompt version 4): 4/6 agree. Both real, user-judged entries (`binnenhof-veldhoven`, `buchterweg-holtum`) agree at Overwegen; the deterministic Hard no example agrees. The two DIFFs are fictional placeholders with guessed tiers (`example-asking-far-above-woz`, `example-flood-depth-high`: expected Overslaan, got Overwegen), so they are not a model regression; more judged real entries, ideally a risky Skip, would test leniency on risk. Real entries freeze the full Buyer Profile, so they are git-ignored (see `config/verdict_regression/README.md`). Status resolved.
