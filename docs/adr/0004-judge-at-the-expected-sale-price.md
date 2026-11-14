# The Verdict judges a house at its Expected Sale Price, not its asking price

Sellers price strategically: some ask well above what a house will fetch, others ask below it to draw bidders. Until now the Case anchored on the asking price: affordability (headroom, monthly costs), the price Flags (`ask_beyond_headroom`, `ask_far_above_woz`, `ask_far_above_comparables`) and, with thin comparables, the Walk-away Maximum (asking price plus the average overbid). An over-asked house could thus be ruled out, even by a deterministic Hard no on a "boven budget" deal-breaker, while a realistic bid would fit. An under-asked house could look affordable while it would sell well above the household's reach.

We decided that the Case derives an **Expected Sale Price** (_Dutch UI_ **Verwachte verkoopprijs**): what the house is expected to sell for, from evidence independent of its own asking price. With sufficient comparables it is their value plus the average overbid for the soort woning, since comparables carry asking prices; otherwise the indexed WOZ value, weakly grounded; otherwise there is none. Affordability, the price Flags, the Walk-away Maximum and the Verdict all rest on it. The asking price stays a Listing fact. Its gap to the Expected Sale Price is shown as **Prijsstelling** (how the seller has priced the house). It feeds the opening bid tactics and never counts as a pro or con on its own.

We rejected using the opening bid as the anchor: the model proposes it in the same answer as the Verdict, so judging by it would be circular and would move judgement out of the deterministic Case (ADR-0001). We rejected keeping asking price plus overbid as a fallback: it carries exactly the seller's pricing bias this decision removes. When no independent evidence exists, the Case says the Expected Sale Price is unknown instead of guessing.

## Consequences

- The Expected Sale Price is computed deterministically in the Case, with its basis, provenance and whether it is weakly grounded (ADR-0001 holds).
- Comparables on funda carry asking prices, not sale prices; the average overbid corrects them only on average. That weakness stays until a source of registered sale prices is added.
- A "te duur"/"boven budget" deal-breaker forces a Hard no only when a strongly grounded Expected Sale Price exceeds what the household can afford. On the WOZ basis the Flag is raised and the model weighs it: a coarse estimate must not reject a house before the model sees it.
- Without an Expected Sale Price there is no headroom, no price Flag, no Walk-away Maximum and no opening bid; the Bid Advice gives conditions only and asks for comparables. The Verdict may not be Must buy; the Verdict service enforces that.
- The Flag rule set, the Case shape and the Verdict prompt change versions, so earlier Verdicts become Achterhaald, and the regression set is re-run.
