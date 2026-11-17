# 04: Verdict judges at the Expected Sale Price

**What to build:** Spec "Verdict" (decisions 6, 7). The prompt anchors the Oordeel on `case.metrics.expected_sale_price`, uses Prijsstelling only for the opening bid tactics, and says plainly when the price cannot be judged. Validation rejects Must buy without an Expected Sale Price, and an opening bid without a Walk-away Maximum. The monthly cost at the Walk-away Maximum goes into the model's input. Bid Advice carries `expected_sale_price` and `monthly_cost_at_expected_sale_price`.

**Blocked by:** 02, 03

**Status:** resolved

- [x] `VERDICT_INSTRUCTION` rewritten for the Expected Sale Price; `VERDICT_PROMPT_VERSION` bumped
- [x] Validation: `must_buy_without_expected_sale_price`; opening bid without a Walk-away Maximum rejected; conditions-only Bid Advice accepted
- [x] `case.walk_away.monthly_cost` in the input
- [x] Bid Advice fields renamed/added; older Verdicts still render
- [x] Regression example entries re-judged (`example-asking-far-above-woz` replaced by `example-asking-far-above-expected-price`, expected tier consider; `example-efficient-family-home` note updated; flood and label entries unchanged)
- [ ] Real-model regression run (user, costs money; not run by the agent)
