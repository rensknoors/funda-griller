# The Guide Bid comes from the Case; the model adjusts it within a band

The model used to propose the opening bid freely, bounded only above by the Walk-away Maximum. With nothing to anchor it, it fell back on asking price minus a round amount (Europalaan 26: asking €525.000, opening €515.000, Walk-away Maximum €582.813). We decided that the Case derives a **Guide Bid** (_Dutch UI_ **Richtbod**) from the Expected Sale Price (ADR-0004), discounted by the Prijsstelling and the time on the market, capped at the Walk-away Maximum. The model proposes the opening bid within ±3% of it, never above the Walk-away Maximum, and must explain any deviation; a bid outside those bounds, or a deviation without a reason, is a validation problem.

We rejected a fully model-driven bid, which is the anchoring pattern we are removing. We rejected a fully deterministic bid, because the model sees Observations, Findings and Documents that the formula cannot weigh. The split follows ADR-0001: the Case derives what can be derived, the model judges the rest.

## Consequences

- The Case shape, the Verdict prompt and its validation change versions, so earlier Verdicts become Achterhaald.
- Discounts, thresholds, the band and the rounding step are configured in `config/defaults.toml`. The values start as plausible guesses and are tuned against the regression set.
- Time on the market is counted from the first `price_history` date to the snapshot's fetch date, so the Guide Bid is reproducible per snapshot.
- The Guide Bid is only as good as the Expected Sale Price, which rests on asking prices until registered sale prices are available (ticket 06).
- The discount per Prijsstelling is one configured figure each (hoog ingezet 6%, marktconform 2,5%, laag ingezet 0%: the middle of the 5-7% and 2-3% ranges), in `[guide_bid]`. The discount breakdown is a map of components: Prijsstelling, and with a readable price history days on the market and the price reduction (the Case metric `market_tempo`); without one the tempo is unknown and adds nothing.
- The model's reason for a deviation is required, stored and shown: an opening bid that differs from the Guide Bid without a reason is a validation problem, like a bid outside the band or above the Walk-away Maximum.
- There is no Guide Bid without an asking price: no asking price means no Prijsstelling. The opening bid is then bounded by the Walk-away Maximum only.
- The Guide Bid and the opening bid may lie above the asking price (laag ingezet). The Biedadvies and the export then say so plainly, with the Verwachte verkoopprijs beside the Openingsbod.
- A house sold under reservation (funda's "Verkocht onder voorbehoud", the Listing status `sold_under_reservation` in `listing_status_map`) gets conditions only; an opening bid there is a validation problem.

## Reversed: no cap at the asking price (2026-11-17)

The Guide Bid and the opening bid were first capped at the asking price, on the view that bidding above it is the buyer's own choice. For a house that is laag ingezet that cap put the advice at a bid that cannot win: a seller who asks low draws several bidders, often in a one-round bidding procedure, so a bid at the asking price is hopeless. The asking price is the seller's marketing, not an anchor. The cap and the validation that rejected an opening bid above the asking price are dropped; the Walk-away Maximum, the ±3% band and the required deviation reason stay. Verdicts made under the cap still render it.
