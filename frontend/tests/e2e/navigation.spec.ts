import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('public landing header blog link works', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('navigation').getByRole('link', { name: 'Blog' }).click();
    await expect(page).toHaveURL('/blog');
  });

  test('public chat route is reachable without login', async ({ page }) => {
    await page.goto('/chat');

    await expect(page).toHaveURL('/chat');
    await expect(page.getByRole('textbox', { name: /message/i })).toBeVisible();
  });

  test('404 page displays for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page');

    await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Go Home' })).toBeVisible();
  });
});
