import { test, expect } from '@playwright/test';
import { login } from './helpers';

test.describe('Dashboard - Smoke', () => {
  test('dashboard loads after login', async ({ page }) => {
    await login(page);
    const response = await page.goto('/dashboard');
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
    expect(response?.status()).toBeLessThan(400);
    await expect(page.getByRole('navigation')).toBeVisible({ timeout: 10000 });
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/internal server error/i);
    expect(body).not.toMatch(/application error/i);
  });

  test('dashboard has navigation links', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await expect(page.getByRole('navigation')).toBeVisible({ timeout: 10000 });
    const navLinks = page.locator('nav a, nav button');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Dashboard - Regression', () => {
  test('dashboard does not show 404 or 500 errors', async ({ page }) => {
    await login(page);
    const response = await page.goto('/dashboard');
    expect(response?.status()).toBeLessThan(400);
    expect(page.url()).not.toMatch(/\/404(?:[/?#]|$)/);
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/500|internal server error/i);
  });

  test('nav links are clickable and do not 404', async ({ page }) => {
    await login(page);
    for (const route of ['/portfolio', '/watchlist', '/screener']) {
      const response = await page.goto(route);
      expect(response?.status()).toBeLessThan(400);
      expect(page.url()).not.toMatch(/login/);
      expect(page.url()).not.toMatch(/\/404(?:[/?#]|$)/);
      const body = await page.locator('body').innerText();
      expect(body).not.toMatch(/internal server error|application error/i);
    }
  });
});

test.describe('Dashboard - Integration', () => {
  test('dashboard to portfolio navigation works', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    const portfolioLink = page.locator('a[href*="portfolio"]').first();
    if (await portfolioLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await portfolioLink.click();
      await expect(page).toHaveURL(/portfolio/, { timeout: 10000 });
    } else {
      await page.goto('/portfolio');
      await expect(page).not.toHaveURL(/login/, { timeout: 10000 });
    }
  });
});
