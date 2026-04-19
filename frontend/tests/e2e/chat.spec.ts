import { test, expect } from '@playwright/test';

test.describe('Chat Page', () => {
  test('displays chat interface', async ({ page }) => {
    await page.goto('/chat');

    await expect(page).toHaveTitle(/Chat/);
  });

  test('message input is visible and interactive', async ({ page }) => {
    await page.goto('/chat');

    const input = page.getByRole('textbox', { name: /message/i });
    await expect(input).toBeVisible();
    await expect(input).toBeEditable();
  });

  test('send button is visible', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.getByRole('button', { name: /send/i })).toBeVisible();
  });

  test('sidebar has new chat button', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.getByRole('button', { name: /new chat/i })).toBeVisible();
  });
});
