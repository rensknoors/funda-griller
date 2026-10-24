# 01: Scaffold and test harness

**What to build:** One command starts the Python backend (FastAPI, SQLite) and the Vite+ / React / Base UI frontend locally. The API test harness runs the app against a temporary SQLite file with fakes for the three outside-world ports (Listing provider, Source client, LLM client), and a Playwright smoke test is wired up. This is prefactoring: the visible result is a running app with one health route rendering, and a green test run.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] A single documented command starts backend and frontend; the frontend renders a page that confirms it can reach the API
- [x] The API test harness boots the app on a temp SQLite file and exposes fakes for Listing provider, Source client and LLM client
- [x] A trivial API test passes through the harness without any network access
- [x] A Playwright smoke test runs against the API with fakes and passes
- [x] Model identifiers, API keys and Source time-to-lives are read from configuration, not code
- [x] Python dependencies are pinned, including `tls-client` below 2.0; `.gitignore` covers virtualenvs, local DB files and downloaded media
