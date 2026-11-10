# The own offered mortgage rate may reach the LLM

The Boundaries rule in `CODING_STANDARDS.md` lets only derived Buyer Profile figures and preferences reach the LLM. The mortgage rate a household was offered (`offered_rate_nhg`, `offered_rate_no_nhg`) is a raw Buyer Profile value, yet the user decided in ticket 31 (`.scratch/funda-griller/issues/31-own-offered-mortgage-rate.md`, 2026-11-09) that it may reach the LLM, so the Verdict can say which rate its figures rest on. This is a sanctioned exception to that rule, and the only one for a finance field.

What passes: `reduce_profile` carries, per loan route, the rate used, its source (`own` or `market`) and, for the market rate, its date (`mortgage_rates`); the Case's `rules.rates` carries the same with its provenance. A market rate is a public snapshot, not household data.

## Consequences

- Nothing else from the finances follows this path: income, balances, debts and addresses stay out of what the LLM receives. Debts in particular are shown in the app (Gevolgen, Dossier, export) but are removed from the Case before the Verdict service sends it (ticket 30).
- The Markdown export still rounds the own rate to 0,1 procentpunt; that is an export privacy rule, separate from this decision.
- A further raw finance field reaching the LLM needs its own decision, not an appeal to this one.
