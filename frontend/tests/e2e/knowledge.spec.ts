import { test, expect } from '@playwright/test';

test.describe('Knowledge Base Page', () => {
  test('displays knowledge base interface', async ({ page }) => {
    await page.goto('/knowledge');

    await expect(page).toHaveTitle(/Knowledge/);
    await expect(
      page.getByRole('heading', { level: 1 })
    ).toContainText('Knowledge Base');
  });

  test('document list is visible', async ({ page }) => {
    await page.goto('/knowledge');

    await expect(page.getByPlaceholder(/search documents/i)).toBeVisible();
  });

  test('new document button is visible', async ({ page }) => {
    await page.goto('/knowledge');

    await expect(page.getByRole('button', { name: /new document/i })).toBeVisible();
  });

  test('upload button is visible', async ({ page }) => {
    await page.goto('/knowledge');

    await expect(page.getByRole('button', { name: /upload/i })).toBeVisible();
  });
});
