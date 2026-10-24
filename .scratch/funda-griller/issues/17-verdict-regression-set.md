# 17: Verdict regression set

**What to build:** A harness that runs 5 to 10 stored Listings, each with the user's expected tier, through the real Verdict model on demand and reports agreement. It is not part of the normal test run. Its purpose is to gate prompt, rule and model changes.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

- [ ] A set of stored Listings with expected tiers can be defined and extended
- [ ] A single command runs the set against the configured real model and prints expected versus actual per Listing
- [ ] The harness is excluded from the default test run and clearly marked as costing money
- [ ] Results record the model identifier, rule version and prompt version used
