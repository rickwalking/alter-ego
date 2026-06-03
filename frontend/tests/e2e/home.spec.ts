import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('displays landing page with correct title', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle(/Alter Ego|Pedro Marins/);
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toContainText('Chat with my');
    await expect(heading).toContainText('Alter-Ego');
  });

  test('homepage has no dashboard neon sidebar', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('v2.0 · Neon Shell')).not.toBeVisible();
    await expect(page.getByRole('link', { name: 'Knowledge' })).not.toBeVisible();
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

  // Feature: Landing page CSS effects and responsive layout
  // Scenario: Homepage hero stacks on mobile with terminal first
  test('hero terminal appears above heading on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    const terminal = page.getByText('alter-ego/session');
    const heading = page.getByRole('heading', { level: 1 });

    const terminalBox = await terminal.boundingBox();
    const headingBox = await heading.boundingBox();

    expect(terminalBox).not.toBeNull();
    expect(headingBox).not.toBeNull();
    if (terminalBox && headingBox) {
      expect(terminalBox.y).toBeLessThan(headingBox.y);
    }
  });

  // Scenario: Primary CTA has hover lift on desktop
  test('primary CTA lifts on hover at desktop width', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');

    const cta = page.getByTestId('cta-primary');
    await cta.hover();
    await expect(cta).toHaveCSS('transform', /matrix/);
  });

  // Scenario: Secondary feature card lifts on hover
  test('secondary feature card lifts on hover at desktop width', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');

    const card = page.getByTestId('feature-secondary-0');
    await card.scrollIntoViewIfNeeded();
    await card.hover();
    await expect(card).toHaveCSS('transform', /matrix/);
  });

  // Scenario: Reduced motion disables hover transform
  test('primary CTA does not lift when reduced motion is preferred', async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');

    const cta = page.getByRole('link', { name: 'Start Chatting' });
    await cta.hover();

    const transform = await cta.evaluate((el) =>
      window.getComputedStyle(el).transform
    );
    expect(transform).toBe('none');
  });

  test('homepage navigation does not log console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    page.on('pageerror', (err) => {
      errors.push(err.message);
    });

    await page.goto('/');
    await page.getByRole('navigation').getByRole('link', { name: 'Chat' }).click();
    await expect(page).toHaveURL('/chat');
    await page.goto('/');
    await expect(page.getByTestId('hero-heading')).toBeVisible();

    expect(errors).toEqual([]);
  });
});
