# 21: Renovation Estimate split by urgency

**What to build:** A **Renovation Estimate** (_Verbouwingsraming_) in the Case: what the house will cost to renovate, split into three urgency classes, **Direct nodig**, **Binnen 5 jaar** and **Optioneel**. Items are derived deterministically from Case facts by a versioned cost table (ADR-0001: the Case holds no judgement; the Verdict only cites the estimate). Each item has a low–high cost range, cites the facts that triggered it with their provenance, and is marked estimated. The Direct nodig midpoint lowers the house's affordable maximum and the Walk-away Maximum. Covers spec story 54's "likely renovation cost" of a poor energielabel.

**Blocked by:** 11 (Photos and Observations), 12 (Documents and Findings), 07 (Energielabel and WOZ Sources)

**Status:** ready-for-agent

### Cost table

- [ ] New versioned TOML cost table, loaded like the Flag rules. Per item: `id`, Dutch label, urgency class, triggers, cost basis, low and high unit cost, `supersedes` list, `source` (e.g. Milieu Centraal, consumer price guide) and `price_year`. Table has a `version`
- [ ] Seeded from public average prices; the user maintains the figures by hand
- [ ] Cost basis is one of: fixed; per m² `living_area` (interior, insulation); size band on `living_area` (<80, 80–150, >150 m²) for roof and facade. A missing `living_area` uses the middle band and the item says so

### Triggers and items

- [ ] Triggers read Observations (`observation.*`), Findings, Source facts (energielabel) and Listing facts (`construction_year`, `heating`), in the same condition vocabulary as the Flag rules
- [ ] Build-year triggers (e.g. asbestos survey before 1994, foundation check before 1930, insulation before 1975 with no energielabel) produce inspection items (survey cost, not full repair), marked "op basis van bouwjaar"
- [ ] One item per `id`: when several facts trigger it, it cites all of them and takes the most urgent class. An item in another item's `supersedes` list is dropped when that item is present (e.g. `renovation_needed: full` replaces kitchen, bathroom and cosmetic items)
- [ ] Items without a trigger fact are left out, never guessed; the Case lists the missing inputs (no photos, no Vragenlijst, no energielabel)
- [ ] The estimate is the same for every Buyer Profile: `renovation_tolerance` only steers the Verdict
- [ ] The estimate is built for every Case, Hard no included

Starting triggers (seed, adjust while building):

- Direct nodig: damp or mould visible, roof poor, facade poor, seller-stated leaks/foundation/asbestos Findings, `renovation_needed: full`
- Binnen 5 jaar: kitchen or bathroom past a configured age, roof or facade fair, energielabel E–G (insulation, glazing), old boiler (cv-ketel) or wiring from the Vragenlijst
- Optioneel: `renovation_needed: cosmetic`, energy upgrades on label C–D (heat pump, solar)

### Effect on the numbers

- [ ] Per class: low and high totals; the midpoint of Direct nodig is the figure used below
- [ ] Affordable maximum for the house becomes `(available − Direct nodig midpoint) / (1 + transfer tax rate)`
- [ ] Walk-away Maximum (ticket 20) becomes `min(that affordable maximum, (basis − Direct nodig midpoint) × (1 + margin))` for the comparables and asking-price bases; `WalkAwayDerivation` records the subtraction
- [ ] Both subtractions show in the Bid Advice **Hoe berekend** expander
- [ ] New con Flag rule `renovation_direct_high` when the Direct nodig midpoint exceeds a threshold in the Flag rules (default €25,000); deal-breaker aliases include "opknapper"

### Case, Verdict and UI

- [ ] `built_from` records the cost table version, so a table change makes Verdicts Achterhaald
- [ ] The Verdict prompt receives the classes, totals and items with provenance; `VERDICT_PROMPT_VERSION` is bumped and the regression set re-run against the real model (user step, as in ticket 20)
- [ ] Dossier group **Verbouwingskosten**: three classes, euro ranges, "geschat" stamps, evidence links as in Signalen, "prijspeil <year>", and the missing-inputs note
- [ ] Comparison view (ticket 15) gets a **Direct nodig** column
- [ ] GLOSSARY.md gets **Renovation Estimate** (_Dutch UI_: **Verbouwingsraming**; classes **Direct nodig**, **Binnen 5 jaar**, **Optioneel**); the Walk-away Maximum entry mentions the Direct nodig subtraction

### Tests

- [ ] API tests: items from Observations, Findings, energielabel and build year; dedupe and `supersedes`; no photos or Documents (missing inputs listed); missing `living_area` (middle band); affordable maximum and Walk-away Maximum with and without Direct nodig items; `renovation_direct_high` Flag; cost-table version change marks a Verdict Achterhaald; Hard no still skips the LLM and still carries the estimate

## Notes

- Changes `verdict.derive_walk_away_maximum` from ticket 20. Ticket 20's code is done; only its real-model regression run is pending, which this ticket's re-run can cover.
- Bouwdepot (construction deposit) and the extra mortgage room for energy measures are out of scope.

## Comments

- Grilled (user, 2026-10-26): deterministic table over LLM estimate; Direct nodig midpoint subtracts from the basis of the Walk-away Maximum and from the available funds of the affordable maximum (a separate "cash needed" line would always fall short, because the affordable maximum already spends all own funds); `renovation_tolerance` steers the Verdict only; fixed 5-year horizon; ranges, not single figures; build-year triggers allowed as inspection items; prices from public averages with source and year; size bands for roof and facade; dedupe with `supersedes`; con Flag on a high Direct nodig total; estimate on every Case; Direct nodig column in the comparison view.
