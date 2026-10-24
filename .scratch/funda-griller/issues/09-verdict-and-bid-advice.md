# 09: Verdict and Bid Advice

**What to build:** The LLM client port with its Gemini adapter, and the Verdict service. The Verdict model receives the Case plus the reduced Buyer Profile and returns a tier (Must buy, Consider, Skip, Hard no), plain-language reasoning that cites Flags, and Bid Advice: opening bid, Walk-away Maximum and suggested conditions. A Hard no from deal-breakers skips the LLM entirely. The Verdict page shows the result. Verdicts are versioned against Case, profile and model and can be re-run; editing the profile triggers re-evaluation. v1 is complete when this ships.

**Blocked by:** 02 (Resolve open risks), 07 (Energielabel and WOZ Sources), 08 (Flags and deterministic Hard no)

**Status:** ready-for-agent

- [ ] The Verdict is one of exactly four tiers; an invalid model response is rejected and reported
- [ ] A deal-breaker Hard no never calls the LLM client (asserted in tests)
- [ ] The prompt input contains the Case and the reduced profile only; tests assert that raw income, asset balances and address are absent
- [ ] The model is told each fact's provenance so it can weigh sources differently
- [ ] Bid Advice contains an opening bid, a Walk-away Maximum that is no higher than affordability allows, and suggested conditions
- [ ] Verdicts are stored versioned against Case, profile version and model identifier; re-run on demand creates a new version
- [ ] Editing the Buyer Profile marks existing Verdicts out of date and offers re-evaluation
- [ ] Model identifiers come from configuration (vision and Verdict roles are independent)
- [ ] The Verdict page is built to the design brief
- [ ] API tests use the fake LLM client; a Playwright smoke test walks profile, URL, Case, Verdict
