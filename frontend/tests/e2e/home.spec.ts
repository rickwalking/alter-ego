import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('displays landing page with correct title', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/RAG Chat/);
    await expect(
      page.getByRole('heading', { level: 1 })
    ).toContainText('Chat with my Alter-Ego');
  });

  test('navigation links work', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Chat', exact: true }).click();
    await expect(page).toHaveURL('/chat');

    await page.goto('/');
    await page.getByRole('link', { name: 'Knowledge Base', exact: true }).click();
    await expect(page).toHaveURL('/knowledge');
  });

  test('CTA buttons navigate correctly', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Start Chatting' }).click();
    await expect(page).toHaveURL('/chat');

    await page.goto('/');
    await page.getByRole('link', { name: 'Manage Knowledge' }).click();
    await expect(page).toHaveURL('/knowledge');
  });

  test('feature cards are displayed', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'AI-Powered Chat' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Knowledge Management' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'AI-Powered Insights' })).toBeVisible();
  });
});
