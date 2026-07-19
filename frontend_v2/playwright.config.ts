import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    channel: "chrome",
    trace: "on-first-retry",
    screenshot: "only-on-failure"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: process.env["PLAYWRIGHT_REUSE_SERVER"] === "1",
    timeout: 120_000,
    env: {
      OWNER_SESSION_SECRET: "playwright-owner-secret-at-least-16",
      NEXT_PUBLIC_DISABLE_REACT_DEVTOOLS: "1",
      PROFILE_DATA_FILE: ".data/playwright-profile-records.json",
      BACKEND_API_ORIGIN: process.env["BACKEND_API_ORIGIN"] ?? "http://127.0.0.1:8000"
    }
  }
});
