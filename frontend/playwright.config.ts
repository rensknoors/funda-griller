import { defineConfig } from "@playwright/test";

const apiPort = 8765;
const webPort = 5174;

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: `http://127.0.0.1:${webPort}` },
  webServer: [
    {
      // Backend wired to fakes and a temp SQLite file; no network access.
      command: `uv run uvicorn tests.e2e_app:app --port ${apiPort}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: false,
    },
    {
      command: `npx vp dev --port ${webPort} --host 127.0.0.1`,
      env: { FG_API_URL: `http://127.0.0.1:${apiPort}` },
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: false,
    },
  ],
});
