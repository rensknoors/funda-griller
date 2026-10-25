# Funda Griller

Personal tool: paste a funda listing, get an evidence file (Case) and a Verdict. See `GLOSSARY.md` and `docs/adr/`.

## Run

Needs `uv` and Node.

```
./dev.sh
```

Backend on http://localhost:8000, frontend on http://localhost:5173 (shows whether it can reach the API).

Configuration: copy `.env.example` to `backend/.env`.

Commute travel times (the `commute` Source) need a free OpenRouteService key (`FG_OPENROUTESERVICE_API_KEY`; Standard plan, 500 matrix requests a day, attribution required, no commercial use). Without it the Source is skipped. Commute destination addresses are geocoded by PDOK's Locatieserver (government, no account) and cached in the local SQLite file; OpenRouteService receives coordinates only. Car and bike are computed, the faster counts; public transport is not included.

## Test

```
cd backend && uv run pytest        # API tests, temp SQLite, fakes for Listing provider / Source clients / LLM client, no network
cd frontend && npx tsc --noEmit    # typecheck
cd frontend && npx playwright test # smoke test against the API with fakes
```

First Playwright run: `npx playwright install chromium`.

### Verdict regression set (costs money)

Before changing the Verdict prompt, the Flag rules or the Verdict model, run the stored Listings through the real model and compare with the expected tiers:

```
cd backend && uv run python -m app.verdict_regression run --yes      # one Gemini call per entry
cd backend && uv run python -m app.verdict_regression add <funda_id> --expect consider --name <slug>
```

Not part of `pytest`. The shipped entries are placeholders; see `config/verdict_regression/README.md`.

## Constraints

- `tls-client` stays below 2.0 (pyfunda 3.1.5 breaks on import otherwise).
- Never call pyfunda `search()`.
