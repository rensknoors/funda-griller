import react from "@vitejs/plugin-react";
import { defineConfig } from "vite-plus";

const apiTarget = process.env.FG_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": apiTarget },
  },
});
