import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('displays landing page with correct title', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/RAG Chat/);
    await expect(
      page.getByRole('heading', { level: 1 })
    ).toContainText('Chat with my Alter-Ego');
  });

  test('homepage has no dashboard neon sidebar', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Alter Ego')).not.toBeVisible();
    await expect(page.getByText('v2.0 · Neon Shell')).not.toBeVisible();
  });

  test('header blog link goes to public blog', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('navigation').getByRole('link', { name: 'Blog' }).click();
    await expect(page).toHaveURL('/blog');
  });

  test('CTA buttons navigate correctly', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Start Chatting' }).click();
    await expect(page).toHaveURL('/chat');

    await page.goto('/');
    await page.getByRole('link', { name: 'Explore Blog' }).click();
    await expect(page).toHaveURL('/blog');
  });
});
