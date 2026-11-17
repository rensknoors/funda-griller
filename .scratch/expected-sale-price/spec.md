# Expected Sale Price: judge the house, not the asking price

Decision records: `docs/adr/0004-judge-at-the-expected-sale-price.md` and `docs/adr/0005-guide-bid-from-the-case.md`. Decisions settled with the user on 2026-11-14 (Expected Sale Price) and 2026-11-17 (Guide Bid); see Decisions below.

## Problem Statement

Sellers set the asking price strategically, sometimes above what a house will fetch and sometimes below it to draw bidders. The app anchors on that asking price: headroom (`affordable_maximum − asking_price`), monthly costs, the price Flags and, with thin comparables, the Walk-away Maximum. The result:

- **Missed chances.** A house asked above budget raises `ask_beyond_headroom`. Combined with a "te duur"/"boven budget" deal-breaker it is a deterministic Harde afwijzing, even when comparables put it within reach and a bid under the asking price is realistic.
- **False hope.** An under-asked house looks affordable and gets a positive Oordeel, while it will sell far above the asking price. Monthly costs at the asking price understate what the household will pay.
- **Weak Maximumbod.** With thin comparables the Walk-away Maximum is asking price × (1 + average overbid), so it copies the seller's pricing.
- **Openingsbod hangs on the asking price.** The model proposes the opening bid freely, bounded only by the Walk-away Maximum, and lands just under the asking price (Europalaan 26: asking €525.000, opening €515.000, Maximumbod €582.813).

## Solution

The Case derives an **Expected Sale Price** (_Dutch UI_: **Verwachte verkoopprijs**): what the house is expected to sell for, from evidence independent of its own asking price. The household is advised on that price, not on the asking price:

1. The Expected Sale Price and its basis are computed in the Case.
2. Affordability, headroom and the price Flags are measured at the Expected Sale Price.
3. The Walk-away Maximum is derived from the Expected Sale Price.
4. The Oordeel judges the house at the Expected Sale Price. The asking price only says how the seller has priced it (**Prijsstelling**) and shapes the opening bid.
5. The Case derives a **Guide Bid** (_Dutch UI_ **Richtbod**) from the Expected Sale Price, the Prijsstelling and the time on the market. The model's Openingsbod stays within a band around it.

## User Stories

1. As a buyer, I want to see what the house is expected to sell for, so I don't anchor on a strategic asking price.
2. As a buyer, I want to see how that figure was reached (comparables plus overbid, or indexed WOZ) and whether it is weakly grounded.
3. As a buyer, I want an over-asked house not to be rejected when a realistic bid fits my budget.
4. As a buyer, I want an under-asked house not to look affordable when it will sell above my reach.
5. As a buyer, I want my monthly costs shown at the Expected Sale Price, the price I will most likely pay.
6. As a buyer, I want to see whether the seller asks high or low (Prijsstelling), so I know whether to expect bidding above the asking price or room to bid below it.
7. As a buyer, when there is too little evidence I want to be told plainly that the price cannot be judged and how to fix that (fetch comparables), not a figure quietly copied from the asking price or my budget.
8. As a buyer, I want my "boven budget" deal-breaker to reject houses whose expected sale price is firmly beyond me, not houses whose asking price merely is, and not on a coarse WOZ estimate.
9. As a buyer comparing houses, I want the Woningen list to show and sort by headroom at the Expected Sale Price.
10. As a buyer, I want the opening bid to follow from what the house is expected to sell for and how the seller priced it, not hover just under the asking price.
11. As a buyer, I want to see how the opening bid came about (discount for Prijsstelling and time on the market) and when the model deviates from it, and why.

## Decisions

1. **Basis.** Sufficient comparables → their value plus the average overbid (strong). Otherwise indexed WOZ (weak); thin comparables are shown next to it but do not count. Neither → no Expected Sale Price; never the asking price.
2. **Overbid on comparables.** Comparables carry asking prices, so the average overbid per soort woning is added to their value and named in the derivation.
3. **Prijsstelling band.** Within ±5% of the Expected Sale Price is marktconform, configurable.
4. **Term.** Domain term Expected Sale Price, _Dutch UI_ Verwachte verkoopprijs.
5. **Walk-away premium.** One premium of 5% for both bases, configurable (was 10% on comparables).
6. **No Expected Sale Price, Verdict.** No hard tier cap, but Must buy is not allowed; the Verdict service validates it.
7. **No Expected Sale Price, Bid Advice.** No Walk-away Maximum and no opening bid; conditions only, plus the hint to fetch comparables.
8. **Hard no on a weak basis.** The "boven budget" deal-breaker forces a Hard no only on a strongly grounded Expected Sale Price. On the WOZ basis the Flag is raised as a con and the model weighs it.
9. **Guide Bid.** `expected_sale_price × (1 − discount)`, capped only at the Walk-away Maximum, rounded down to €500. Discount by Prijsstelling: hoog ingezet 5–7%, marktconform 2–3%, laag ingezet 0%. No asking-price cap (changed 2026-11-17, ADR-0005): laag ingezet draws several bidders, often in a one-round bidding procedure, so a bid at the asking price is hopeless; the asking price is the seller's marketing, not an anchor.
10. **Tempo.** Days on the market (first `price_history` date to the snapshot's fetch date, so it is reproducible) over 60 days add 1 point, over 120 days 2 points (not cumulative); a price reduction (first price above the asking price) adds 1 point; the discount is capped at 10%. Without `price_history` the signal does not count and the Biedadvies says the tempo is unknown.
11. **Model adjustment.** The model proposes the Openingsbod within ±3% of the Guide Bid, never above the Walk-away Maximum, and explains any deviation. Outside the band is a validation problem. An Openingsbod above the asking price is allowed (changed 2026-11-17).
12. **Weak basis, sold under reservation.** The same discount applies on a weakly grounded Expected Sale Price, flagged as such. A house sold under reservation gets no Guide Bid: conditions only, with a note.
13. **Term.** Domain term Guide Bid, _Dutch UI_ Richtbod; the Openingsbod is the model's final bid.

## Implementation Decisions

### Expected Sale Price (Case metric `expected_sale_price`)

Computed in `case.py` next to `asking_vs_woz` and `asking_vs_comparables`, provenance `computed`. Shape:

```
{ value, basis: "comparables" | "woz" | null, weakly_grounded,
  overbid: {value, house_type, source, period} | null, low, high, computed_at, provenance }
```

- **Comparables** (coverage `sufficient`): `comparables_value × (1 + average overbid for the soort woning)`. `config/bid_margins.toml` keeps its figures. Its header now describes it as the asking-to-sale correction for comparables, no longer as a margin above the house's own asking price. `weakly_grounded: false`.
- **WOZ**: the indexed WOZ value (`asking_vs_woz.indexed.woz_value`; raw WOZ when the peildatum is outside the index series), no overbid. `weakly_grounded: true`. `asking_vs_woz` must therefore be computed even when the Listing has no asking price; split the WOZ indexing from the comparison.
- **Neither**: `value: null`, `basis: null`.
- `low`/`high`: the interquartile range of the comparables' €/m² × living area, with the same overbid; null on the WOZ basis. It shows the spread, not a confidence interval.

`asking_vs_comparables` and `asking_vs_woz` stay as evidence for the Dossier but no longer drive Flags.

### Prijsstelling (Case metric `asking_vs_expected`)

`asking_price − expected_sale_price` and its percentage, labelled by a configured band (`config/defaults.toml`, `prijsstelling_band = 0.05`): **hoog ingezet** (> +5%), **marktconform**, **laag ingezet** (< −5%). Null when either side is missing. Information only: not a Flag, never counted against the house.

### Affordability and Flags

- `affordability.headroom` = `affordable_maximum − expected_sale_price`; null without one. `monthly_cost`/`monthly_cost_net` are computed at the Expected Sale Price. The affordability engine's price input becomes "the price assessed" rather than "asking price".
- `ask_beyond_headroom` is replaced by `expected_price_beyond_headroom` ("Verwachte verkoopprijs boven je betaalruimte"), class con, raised at headroom < 0, silent without an Expected Sale Price. It keeps the `deal_breaker_aliases`.
- Hard no on those aliases only when the Expected Sale Price is strongly grounded (decision 8). The rule needs a way to say so, e.g. `hard_no_requires = "expected_sale_price.strong"` read by `flags.hard_no`; the Flag itself is raised on either basis.
- `ask_far_above_woz` and `ask_far_above_comparables` are removed.
- Flag rule set `version` bumps; earlier Verdicts become Achterhaald.

### Walk-away Maximum

`min(affordable_maximum, (expected_sale_price − Direct nodig midpoint) × (1 + walk_away_premium))`. `basis` is `"expected_sale_price"`; `weakly_grounded` follows the Expected Sale Price. Without an Expected Sale Price there is no Walk-away Maximum (`None`), replacing the affordability-only fallback. `walk_away_comparables_premium` is renamed `walk_away_premium`, default 0.05. `asking_price_margin` leaves the Case.

### Verdict

- The prompt anchors the Oordeel on `case.metrics.expected_sale_price`, uses `asking_vs_expected` only for the opening bid (through the Guide Bid), and, without an Expected Sale Price, says the price cannot be judged and that comparables should be fetched.
- Validation: `must_buy` without an Expected Sale Price is a problem (`must_buy_without_expected_sale_price`); without a Walk-away Maximum an `opening_bid` is a problem; Bid Advice then carries conditions only.
- The monthly cost at the Walk-away Maximum moves into the model's input (`case.walk_away.monthly_cost`).
- Bid Advice keeps `asking_price` for display, adds `expected_sale_price`; `monthly_cost_at_asking_price` becomes `monthly_cost_at_expected_sale_price`. Older Verdicts keep rendering with the old fields.
- `VERDICT_PROMPT_VERSION` bumps. The regression set is re-run, and the example entries' expected tiers are re-judged: `example-asking-far-above-woz` loses its premise.

### Guide Bid (Case metric `guide_bid`)

Computed in the Verdict service next to `derive_walk_away_maximum`, since it is capped by it. Shape: `{ value, discount, breakdown: {prijsstelling, days_on_market, price_reduction}, weakly_grounded, capped_by }` (`capped_by` is `walk_away_maximum` or null; Verdicts made before 2026-11-17 may carry `asking_price` and still render it), null without a Walk-away Maximum or when sold under reservation. All figures (discounts per Prijsstelling, tempo thresholds and points, the 10% cap, the band, the rounding step) live in `config/defaults.toml`. It goes into the model's input as `case.guide_bid`; Bid Advice carries it with its breakdown. Tickets 07 (Prijsstelling) and 08 (tempo); `VERDICT_PROMPT_VERSION` bumps with them.

### UI (Dutch)

- Dossier: a **Verwachte verkoopprijs** block with value, range, basis ("op basis van 7 vergelijkbare woningen, incl. 5,9% gemiddeld overbod" / "op basis van de WOZ-waarde naar vandaag"), **Zwak onderbouwd** when weak, and **Prijsstelling** (e.g. "Vraagprijs 8% boven verwachte verkoopprijs: hoog ingezet").
- Woningen list and cards: "Ruimte boven vraag" becomes **Ruimte boven verwachte prijs**, with the sort key following. "–" plus "Haal vergelijkbare woningen op" when absent.
- Biedadvies: maandlasten **bij verwachte verkoopprijs**. Without an Expected Sale Price: no Maximumbod or Openingsbod, the Voorwaarden, and "Haal vergelijkbare woningen op voor een Maximumbod".
- Biedadvies shows the **Verwachte verkoopprijs** right beside the Openingsbod, so the buyer sees what the house will likely sell for and what to open with at a glance. When the Openingsbod or Richtbod lies above the asking price it says so plainly: "12,4% boven de vraagprijs: laag ingezet, reken op overbieden" (the laag ingezet clause only when that is the Prijsstelling).
- Biedadvies shows the Openingsbod; when it differs from the Richtbod, the Richtbod and the model's reason appear beside it, with the discount breakdown (Prijsstelling, dagen te koop, prijsverlaging) or "Tempo onbekend". A house sold under reservation shows conditions and "Verkocht onder voorbehoud".
- Markdown export follows the Dossier and Biedadvies, including the Verwachte verkoopprijs line beside the Openingsbod and the "boven de vraagprijs" note.

### Glossary

**Guide Bid** (_Dutch UI_ **Richtbod**) is already added, with Bid Advice updated. Add **Expected Sale Price** (_Dutch UI_ **Verwachte verkoopprijs**; _Avoid_ market value, valuation, taxatie, realistic price) and **Prijsstelling**. Rewrite Walk-away Maximum (basis is the Expected Sale Price; none without one) and update Comparable (its asking price plus the average overbid feeds the Expected Sale Price) and Hard no (a price deal-breaker needs a strongly grounded Expected Sale Price).

## Testing Decisions

- Unit (`case`): Expected Sale Price per basis (sufficient comparables with overbid; thin comparables → WOZ; indexed vs raw WOZ; WOZ without an asking price; neither → null); Prijsstelling at the band edges.
- Unit (`affordability`, `flags`): headroom and monthly costs at the Expected Sale Price; `expected_price_beyond_headroom` raises at < 0 and stays silent without one; the deal-breaker Hard no only on a strong basis, the Flag on both.
- Scenario tests for the motivating cases: an over-asked house within reach (no Flag, no Hard no); an under-asked house beyond reach (Flag raised, Hard no with the deal-breaker on a strong basis).
- Unit (`verdict`): Guide Bid per Prijsstelling band (laag ingezet above the asking price), the Walk-away Maximum cap, rounding, tempo thresholds and the 10% cap, missing history, weak basis, none when sold under reservation, the ±3% band validation; Walk-away Maximum from the Expected Sale Price, affordability binding, none without one; validation of Must buy and opening bid without an Expected Sale Price.
- API: Case and comparison payloads carry the new fields; old Verdicts still render.
- e2e: Dossier shows Verwachte verkoopprijs and Prijsstelling; the list sorts by the new headroom; Biedadvies without an Expected Sale Price shows conditions and the hint.
- Regression set re-run against the real model (costs money, user runs it), with new cases: marktconform (Europalaan-26-like), hoog ingezet (bid far below asking), laag ingezet (bid around the Expected Sale Price, above asking), 120+ days with a price reduction.

## Out of Scope

- Registered sale prices (Kadaster, funda "verkocht voor"): research ticket 06. If found, they become the strongest basis and the overbid correction falls away for them.
- A statistical valuation model (hedonic regression, AVM).
- Regional market trends beyond the national CBS index already used for WOZ.
