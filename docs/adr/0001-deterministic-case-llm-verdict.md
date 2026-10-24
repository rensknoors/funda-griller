# Case is deterministic; only the Verdict judges

A house is assessed in two stages. The Case (facts, computed metrics, Flags from versioned rules, affordability) is built deterministically and contains no judgement; the LLM then reads the Case plus a reduced Buyer Profile and returns the Verdict and Bid Advice. LLM extraction from photos and Documents (Observations, Findings) counts as fact-gathering, not judgement: it runs once at ingestion or upload, is stored with provenance, and is reused rather than regenerated.

We rejected a single LLM pass over raw data because it is unauditable and unreproducible: you cannot tell why a house got its rating or whether a prompt change altered it. We rejected a purely numeric score because tiering a house against a household's circumstances needs reasoning that rules express poorly. Deal-breakers from the Buyer Profile force a Hard no deterministically, before the LLM runs.

## Consequences

- Every Flag must cite its rule and evidence; the Verdict may cite Flags but never creates them.
- Prompt and rule changes are checked against a regression set of Listings with expected tiers.
- The Verdict is told each fact's provenance (Listing, Source, Observation, Finding) so it can weigh seller-stated claims below official registers.
