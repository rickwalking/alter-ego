import { test as setup, expect } from "@playwright/test";

const authFile = "tests/e2e/.auth/admin.json";

const ADMIN_EMAIL = process.env.PLAYWRIGHT_E2E_EMAIL ?? "admin@alterego.app";
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_E2E_PASSWORD ?? "TestPass123!";

setup("authenticate as admin", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Email" }).fill(ADMIN_EMAIL);
  await page.getByRole("textbox", { name: "Password" }).fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
  await page.context().storageState({ path: authFile });
});
