# 20: Derive the Walk-away Maximum instead of capping the model's number

**What to build:** Spec story 66 asks for a Walk-away Maximum "derived from comparables and my affordability, not invented". Today (ticket 14) the Verdict model proposes the figure and the Verdict service only rejects it above `bid_limits` (affordable maximum, and comparables value plus `walk_away_comparables_premium` when coverage is sufficient). Make the Walk-away Maximum a deterministic figure the Verdict service computes, and let the model supply only the opening bid and conditions (or a reasoned discount below the derived figure).

**Blocked by:** 14 (Comparables and Walk-away Maximum grounding), 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

- [ ] With sufficient comparables, the Walk-away Maximum is `min(affordable maximum, comparables value × (1 + premium))`, computed by the Verdict service and shown with its derivation in the Bid Advice "hoe berekend" expander
- [ ] With thin or missing comparables, the behaviour is decided (see Comments) and stated plainly in the Bid Advice
- [ ] The Verdict prompt and schema no longer ask the model for a free Walk-away Maximum; `VERDICT_PROMPT_VERSION` is bumped and the regression set re-run
- [ ] The opening bid is still validated to be at or below the Walk-away Maximum
- [ ] API tests cover sufficient, thin and no comparables, and affordability binding below comparables

## Comments

- Found by the code review of `integration/funda-griller` (2026-10-25). Not done in the review-fix pass because it is a product decision, not a bug fix: falling back to the affordable maximum when comparables are thin would advise walking away at the household's ceiling (often far above the asking price), which reads worse than today's capped model figure.
- Open: with thin comparables, use the WOZ value (third-party) plus a premium, the asking price plus a premium, keep the model's capped figure marked as an estimate, or give no Walk-away Maximum at all.
