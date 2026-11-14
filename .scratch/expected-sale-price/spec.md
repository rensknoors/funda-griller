# Expected Sale Price: judge the house, not the asking price

Decision record: `docs/adr/0004-judge-at-the-expected-sale-price.md`. Decisions settled with the user on 2026-11-14 (see Decisions below).

## Problem Statement

Sellers set the asking price strategically, sometimes above what a house will fetch and sometimes below it to draw bidders. The app anchors on that asking price: headroom (`affordable_maximum − asking_price`), monthly costs, the price Flags and, with thin comparables, the Walk-away Maximum. The result:

- **Missed chances.** A house asked above budget raises `ask_beyond_headroom`. Combined with a "te duur"/"boven budget" deal-breaker it is a deterministic Harde afwijzing, even when comparables put it within reach and a bid under the asking price is realistic.
- **False hope.** An under-asked house looks affordable and gets a positive Oordeel, while it will sell far above the asking price. Monthly costs at the asking price understate what the household will pay.
- **Weak Maximumbod.** With thin comparables the Walk-away Maximum is asking price × (1 + average overbid), so it copies the seller's pricing.

## Solution

The Case derives an **Expected Sale Price** (_Dutch UI_: **Verwachte verkoopprijs**): what the house is expected to sell for, from evidence independent of its own asking price. The household is advised on that price, not on the asking price:

1. The Expected Sale Price and its basis are computed in the Case.
2. Affordability, headroom and the price Flags are measured at the Expected Sale Price.
3. The Walk-away Maximum is derived from the Expected Sale Price.
4. The Oordeel judges the house at the Expected Sale Price. The asking price only says how the seller has priced it (**Prijsstelling**) and shapes the opening bid tactics.

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

## Decisions

1. **Basis.** Sufficient comparables → their value plus the average overbid (strong). Otherwise indexed WOZ (weak); thin comparables are shown next to it but do not count. Neither → no Expected Sale Price; never the asking price.
2. **Overbid on comparables.** Comparables carry asking prices, so the average overbid per soort woning is added to their value and named in the derivation.
3. **Prijsstelling band.** Within ±5% of the Expected Sale Price is marktconform, configurable.
4. **Term.** Domain term Expected Sale Price, _Dutch UI_ Verwachte verkoopprijs.
5. **Walk-away premium.** One premium of 5% for both bases, configurable (was 10% on comparables).
6. **No Expected Sale Price, Verdict.** No hard tier cap, but Must buy is not allowed; the Verdict service validates it.
7. **No Expected Sale Price, Bid Advice.** No Walk-away Maximum and no opening bid; conditions only, plus the hint to fetch comparables.
8. **Hard no on a weak basis.** The "boven budget" deal-breaker forces a Hard no only on a strongly grounded Expected Sale Price. On the WOZ basis the Flag is raised as a con and the model weighs it.

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

- The prompt anchors the Oordeel on `case.metrics.expected_sale_price`, uses `asking_vs_expected` only for the opening bid tactics, and, without an Expected Sale Price, says the price cannot be judged and that comparables should be fetched.
- Validation: `must_buy` without an Expected Sale Price is a problem (`must_buy_without_expected_sale_price`); without a Walk-away Maximum an `opening_bid` is a problem; Bid Advice then carries conditions only.
- The monthly cost at the Walk-away Maximum moves into the model's input (`case.walk_away.monthly_cost`).
- Bid Advice keeps `asking_price` for display, adds `expected_sale_price`; `monthly_cost_at_asking_price` becomes `monthly_cost_at_expected_sale_price`. Older Verdicts keep rendering with the old fields.
- `VERDICT_PROMPT_VERSION` bumps. The regression set is re-run, and the example entries' expected tiers are re-judged: `example-asking-far-above-woz` loses its premise.

### UI (Dutch)

- Dossier: a **Verwachte verkoopprijs** block with value, range, basis ("op basis van 7 vergelijkbare woningen, incl. 5,9% gemiddeld overbod" / "op basis van de WOZ-waarde naar vandaag"), **Zwak onderbouwd** when weak, and **Prijsstelling** (e.g. "Vraagprijs 8% boven verwachte verkoopprijs: hoog ingezet").
- Woningen list and cards: "Ruimte boven vraag" becomes **Ruimte boven verwachte prijs**, with the sort key following. "–" plus "Haal vergelijkbare woningen op" when absent.
- Biedadvies: maandlasten **bij verwachte verkoopprijs**. Without an Expected Sale Price: no Maximumbod or Openingsbod, the Voorwaarden, and "Haal vergelijkbare woningen op voor een Maximumbod".
- Markdown export follows the Dossier and Biedadvies.

### Glossary

Add **Expected Sale Price** (_Dutch UI_ **Verwachte verkoopprijs**; _Avoid_ market value, valuation, taxatie, realistic price) and **Prijsstelling**. Rewrite Walk-away Maximum (basis is the Expected Sale Price; none without one) and update Comparable (its asking price plus the average overbid feeds the Expected Sale Price) and Hard no (a price deal-breaker needs a strongly grounded Expected Sale Price).

## Testing Decisions

- Unit (`case`): Expected Sale Price per basis (sufficient comparables with overbid; thin comparables → WOZ; indexed vs raw WOZ; WOZ without an asking price; neither → null); Prijsstelling at the band edges.
- Unit (`affordability`, `flags`): headroom and monthly costs at the Expected Sale Price; `expected_price_beyond_headroom` raises at < 0 and stays silent without one; the deal-breaker Hard no only on a strong basis, the Flag on both.
- Scenario tests for the motivating cases: an over-asked house within reach (no Flag, no Hard no); an under-asked house beyond reach (Flag raised, Hard no with the deal-breaker on a strong basis).
- Unit (`verdict`): Walk-away Maximum from the Expected Sale Price, affordability binding, none without one; validation of Must buy and opening bid without an Expected Sale Price.
- API: Case and comparison payloads carry the new fields; old Verdicts still render.
- e2e: Dossier shows Verwachte verkoopprijs and Prijsstelling; the list sorts by the new headroom; Biedadvies without an Expected Sale Price shows conditions and the hint.
- Regression set re-run against the real model (costs money, user runs it).

## Out of Scope

- Registered sale prices (Kadaster, funda "verkocht voor"): research ticket 06. If found, they become the strongest basis and the overbid correction falls away for them.
- A statistical valuation model (hedonic regression, AVM).
- Regional market trends beyond the national CBS index already used for WOZ.
