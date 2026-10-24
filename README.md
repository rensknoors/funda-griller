# Funda Griller

Personal tool: paste a funda listing, get an evidence file (Case) and a Verdict. See `GLOSSARY.md` and `docs/adr/`.

## Run

Needs `uv` and Node.

```
./dev.sh
```

Backend on http://localhost:8000, frontend on http://localhost:5173 (shows whether it can reach the API).

Configuration: copy `.env.example` to `backend/.env`.

## Test

```
cd backend && uv run pytest        # API tests, temp SQLite, fakes for Listing provider / Source clients / LLM client, no network
cd frontend && npx tsc --noEmit    # typecheck
cd frontend && npx playwright test # smoke test against the API with fakes
```

First Playwright run: `npx playwright install chromium`.

## Constraints

- `tls-client` stays below 2.0 (pyfunda 3.1.5 breaks on import otherwise).
- Never call pyfunda `search()`.
