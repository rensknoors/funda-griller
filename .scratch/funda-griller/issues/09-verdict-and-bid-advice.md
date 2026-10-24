# 09: Verdict and Bid Advice

**What to build:** The LLM client port with its Gemini adapter, and the Verdict service. The Verdict model receives the Case plus the reduced Buyer Profile and returns a tier (Must buy, Consider, Skip, Hard no), plain-language reasoning that cites Flags, and Bid Advice: opening bid, Walk-away Maximum and suggested conditions. A Hard no from deal-breakers skips the LLM entirely. The Verdict page shows the result. Verdicts are versioned against Case, profile and model and can be re-run; editing the profile triggers re-evaluation. v1 is complete when this ships.

**Blocked by:** 02 (Resolve open risks), 07 (Energielabel and WOZ Sources), 08 (Flags and deterministic Hard no)

**Status:** resolved

- [x] The Verdict is one of exactly four tiers; an invalid model response is rejected and reported
- [x] A deal-breaker Hard no never calls the LLM client (asserted in tests)
- [x] The prompt input contains the Case and the reduced profile only; tests assert that raw income, asset balances and address are absent
- [x] The model is told each fact's provenance so it can weigh sources differently
- [x] Bid Advice contains an opening bid, a Walk-away Maximum that is no higher than affordability allows, and suggested conditions
- [x] Verdicts are stored versioned against Case, profile version and model identifier; re-run on demand creates a new version
- [x] Editing the Buyer Profile marks existing Verdicts out of date and offers re-evaluation
- [x] Model identifiers come from configuration (vision and Verdict roles are independent)
- [x] The Verdict page is built to the design brief
- [x] API tests use the fake LLM client; a Playwright smoke test walks profile, URL, Case, Verdict

## Comments

- Verdict API: `GET/POST /api/listings/{id}/verdict` (history newest first, `out_of_date`, `changed` in case/buyer_profile/rules/model); `GET /api/verdicts/out-of-date` returns `{count, verdicts}` for the post-save "Dit verandert N oordelen" summary. Nothing re-runs by itself.
- The Case's affordability gains `max_price`; the Walk-away Maximum is validated against it. Comparables are not in the Walk-away Maximum yet (ticket 14); the "hoe berekend" expander says so.
- Gemini adapter calls the REST `generateContent` endpoint with a JSON response schema (stdlib HTTP, no SDK). Photo and Document extraction stay unimplemented until tickets 11 and 12.
- The Listing address is part of the Case and does reach the model; the household's own address and commute addresses never do.

