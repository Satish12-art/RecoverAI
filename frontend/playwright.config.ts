import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "cd ../backend && source venv/bin/activate && python main.py",
      url: "http://localhost:8000/api/health",
      timeout: 30000,
      reuseExistingServer: true,
    },
    {
      command: "npm run start",
      url: "http://localhost:3000",
      timeout: 30000,
      reuseExistingServer: true,
    },
  ],
});
