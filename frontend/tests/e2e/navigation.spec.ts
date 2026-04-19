import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('header navigation works from all pages', async ({ page }) => {
    const pages = ['/', '/chat', '/knowledge'];

    for (const path of pages) {
      await page.goto(path);

      await page.getByRole('link', { name: 'Chat', exact: true }).click();
      await expect(page).toHaveURL('/chat');

      await page.goto(path);
      await page.getByRole('link', { name: 'Knowledge Base', exact: true }).click();
      await expect(page).toHaveURL('/knowledge');

      await page.goto(path);
      await page.getByRole('link', { name: 'Pedro Marins' }).click();
      await expect(page).toHaveURL('/');
    }
  });

  test('404 page displays for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page');

    await expect(page.getByText('404')).toBeVisible();
    await expect(page.getByText('Page Not Found')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Go Home' })).toBeVisible();
  });
});
