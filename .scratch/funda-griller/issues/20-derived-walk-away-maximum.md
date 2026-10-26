# 20: Derive the Walk-away Maximum instead of capping the model's number

**What to build:** Spec story 66 asks for a Walk-away Maximum "derived from comparables and my affordability, not invented". Today (ticket 14) the Verdict model proposes the figure and the Verdict service only rejects it above `bid_limits` (affordable maximum, and comparables value plus `walk_away_comparables_premium` when coverage is sufficient). Make the Walk-away Maximum a deterministic figure the Verdict service computes, and let the model supply only the opening bid and conditions (or a reasoned discount below the derived figure).

**Blocked by:** 14 (Comparables and Walk-away Maximum grounding), 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] With sufficient comparables, the Walk-away Maximum is `min(affordable maximum, comparables value × (1 + premium))`, computed by the Verdict service and shown with its derivation in the Bid Advice "hoe berekend" expander
- [x] With thin or missing comparables, the behaviour is decided (see Comments) and stated plainly in the Bid Advice
- [x] The Verdict prompt and schema no longer ask the model for a free Walk-away Maximum; `VERDICT_PROMPT_VERSION` is bumped and the regression set re-run (run 2026-10-26 at prompt version 4, see Comments)
- [x] The opening bid is still validated to be at or below the Walk-away Maximum
- [x] API tests cover sufficient, thin and no comparables, affordability binding below comparables, and neither comparables nor an asking price (added by the code review fixes)

## Comments

- Found by the code review of `integration/funda-griller` (2026-10-25). Not done in the review-fix pass because it is a product decision, not a bug fix: falling back to the affordable maximum when comparables are thin would advise walking away at the household's ceiling (often far above the asking price), which reads worse than today's capped model figure.
- Open: with thin comparables, use the WOZ value (third-party) plus a premium, the asking price plus a premium, keep the model's capped figure marked as an estimate, or give no Walk-away Maximum at all.
- Decided (user, 2026-10-25): with thin or missing comparables the Walk-away Maximum is `min(affordable maximum, asking price × (1 + walk_away_asking_price_margin))`, margin from config (default 5%), and the Bid Advice states plainly that it is weakly grounded because comparables are thin. With sufficient comparables, the formula above. The model no longer supplies a Walk-away Maximum; one it still sends is ignored. With neither sufficient comparables nor an asking price, it falls back to the affordable maximum, also marked weakly grounded.
- Done: `verdict.derive_walk_away_maximum` derives the figure and its derivation (basis, margin, basis maximum, binding limit, weakly grounded); the model gets it as `case.walk_away` and answers only opening bid and conditions; Bid Advice carries `derivation`, shown in "Hoe berekend" and, when weak, as a "Zwak onderbouwd" note next to the Maximumbod. Older Verdicts without `derivation` still render with the old binding-limit line. `VERDICT_PROMPT_VERSION` is 3.
- Pending (box unticked until done): the regression set has not been re-run against the real Verdict model (costs money). The runner works with the fake (`tests/test_verdict_regression.py`). Run `cd backend && uv run python -m app.verdict_regression run --yes` to record prompt version 3.
- Code review fixes (2026-10-25): the regression box is unticked and the Status is `ready-for-human` until the user runs that real-model regression; then tick it and set `resolved`. Also: `verdict.walk_away` is now `derive_walk_away_maximum`, returning a typed `WalkAwayDerivation`; the affordability-only fallback has an API test; GLOSSARY's Walk-away Maximum names that fallback.
- Real-model regression run (user, 2026-10-26, `gemini-3.8-flash`, Flag rule set 11, prompt version 4): 4/6 agree. Both real, user-judged entries (`binnenhof-veldhoven`, `buchterweg-holtum`) agree at Overwegen; the deterministic Hard no example agrees. The two DIFFs are fictional placeholders with guessed tiers (`example-asking-far-above-woz`, `example-flood-depth-high`: expected Overslaan, got Overwegen), so they are not a model regression; more judged real entries, ideally a risky Skip, would test leniency on risk. Real entries freeze the full Buyer Profile, so they are git-ignored (see `config/verdict_regression/README.md`). Status resolved.
