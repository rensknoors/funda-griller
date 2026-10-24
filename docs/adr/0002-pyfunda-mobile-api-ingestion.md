# Ingest Listings via pyfunda (funda's reverse-engineered mobile API)

Listings are fetched server-side with the open-source `pyfunda` library, which calls the `*.funda.io` mobile API endpoints that funda's Android app uses. This gives complete structured data (facts, media, price history) with no HTML scraping, headless browser or CAPTCHA solving, and it fits a Python backend that also hosts the Gemini SDK.

This trades legal footing for completeness. Funda has no public API and its ToS forbids automated collection, so this is the riskier of the options we weighed; a user-triggered browser extension reading the page the user already loaded would have been safer but captures less cleanly. We accept the risk because the tool is personal, single-household, user-initiated and low-volume, and photos are stored locally and never republished.

## Consequences

- The API is undocumented and can break or be blocked at any time. Ingestion sits behind a single Listing provider seam, with manual entry as the fallback; a browser-capture adapter can be added later without touching the Case.
- The backend is Python (FastAPI), not TypeScript.
- Never crawl, bulk-fetch or run this as a service for others; that would invalidate the reasoning above.
