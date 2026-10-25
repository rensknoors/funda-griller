# 17: Verdict regression set

**What to build:** A harness that runs 5 to 10 stored Listings, each with the user's expected tier, through the real Verdict model on demand and reports agreement. It is not part of the normal test run. Its purpose is to gate prompt, rule and model changes.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** resolved

- [x] A set of stored Listings with expected tiers can be defined and extended
- [x] A single command runs the set against the configured real model and prints expected versus actual per Listing
- [x] The harness is excluded from the default test run and clearly marked as costing money
- [x] Results record the model identifier, rule version and prompt version used
