import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests/e2e/.auth/admin.json',
      },
      dependencies: ['setup'],
      // Exclude the real-login setup AND the backend-free auth baseline (AE-0165):
      // auth-baseline runs in its own project with no storageState / no setup.
      testIgnore: [/auth\.setup\.ts/, /auth-baseline\.spec\.ts/],
    },
    {
      // AE-0165: deterministic, backend-free auth baseline. No storageState and
      // no `setup` dependency, so it never triggers the real-backend admin login.
      name: 'auth-baseline',
      testMatch: /auth-baseline\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        stdout: 'ignore',
        stderr: 'pipe',
        timeout: 120_000,
      },
});
