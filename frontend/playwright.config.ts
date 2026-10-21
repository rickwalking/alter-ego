import { defineConfig, devices } from "@playwright/test";

/**
 * The auth-baseline project is deterministic and backend-free: no storageState
 * and no setup dependency, so it never triggers the real-backend admin login.
 * The chromium project ignores it and the real-login setup.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "tests/e2e/.auth/admin.json",
      },
      dependencies: ["setup"],
      testIgnore: [/auth\.setup\.ts/, /auth-baseline\.spec\.ts/],
    },
    {
      name: "auth-baseline",
      testMatch: /auth-baseline\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        stdout: "ignore",
        stderr: "pipe",
        timeout: 120_000,
      },
});
