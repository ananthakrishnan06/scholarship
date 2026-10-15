import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL || "msedge",
    headless: true,
  },
  reporter: [["list"], ["json", { outputFile: "../var/browser-report.json" }]],
  webServer: [
    {
      command:
        "python ../backend/manage.py runserver 127.0.0.1:8001 --noreload",
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      timeout: 60000,
      env: { DJANGO_DEBUG: "true", LLM_PROVIDER: "none" },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 60000,
      env: { BACKEND_URL: "http://127.0.0.1:8001" },
    },
  ],
});
