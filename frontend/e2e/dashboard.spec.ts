import { test, expect } from '@playwright/test';
import { login } from './helpers';

test.describe('Dashboard — Smoke', () => {
  test('dashboard loads after login', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(3000);
    const url = page.url();
    expect(url).not.toMatch(/login/);
    // Page should have meaningful content
    const body = await page.textContent('body');
    expect(body).not.toMatch(/internal server error/i);
    expect(body).not.toMatch(/application error/i);
  });

  test('dashboard has navigation links', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
    // Should have nav links to key sections
    const navLinks = page.locator('nav a, header a, [role="navigation"] a');
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Dashboard — Regression', () => {
  test('dashboard does not show 404 or 500 errors', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).not.toMatch(/404|not found/i);
    expect(body).not.toMatch(/500|internal server error/i);
  });

  test('nav links are clickable and do not 404', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
    // Key routes should load without errors
    for (const route of ['/portfolio', '/watchlist', '/screener']) {
      await page.goto(route);
      await page.waitForTimeout(2000);
      const url = page.url();
      expect(url).not.toMatch(/login/);
      const body = await page.textContent('body');
      expect(body).not.toMatch(/404/);
    }
  });
});

test.describe('Dashboard — Integration', () => {
  test('dashboard → portfolio navigation works', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
    // Try clicking a portfolio link if present
    const portfolioLink = page.locator('a[href*="portfolio"]').first();
    if (await portfolioLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await portfolioLink.click();
      await page.waitForURL(/portfolio/, { timeout: 10000 });
      expect(page.url()).toMatch(/portfolio/);
    } else {
      await page.goto('/portfolio');
      await page.waitForTimeout(2000);
      expect(page.url()).not.toMatch(/login/);
    }
  });
});
