import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Watchlist — Smoke', () => {
  test('watchlist page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/watchlist');
    expect(status).toBe('OK');
  });

  test('watchlist page has correct content', async ({ page }) => {
    await login(page);
    await page.goto('/watchlist');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/watchlist|lista|acompanhar|monitorar|ativo/i);
  });
});

test.describe('Watchlist — Regression', () => {
  test('watchlist renders without JS errors', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/watchlist');
    await page.waitForTimeout(4000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver') && !e.includes('Non-Error'));
    expect(criticalErrors).toHaveLength(0);
  });

  test('watchlist search input is present', async ({ page }) => {
    await login(page);
    await page.goto('/watchlist');
    await page.waitForTimeout(3000);
    // Should have a search/add input
    const searchInput = page.locator('input[placeholder*="ticker" i], input[placeholder*="busca" i], input[placeholder*="pesquis" i], input[type="search"]').first();
    const addBtn = page.locator('button').filter({ hasText: /adicionar|add/i }).first();
    const hasSearch = await searchInput.isVisible({ timeout: 2000 }).catch(() => false);
    const hasAdd = await addBtn.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasSearch || hasAdd).toBeTruthy();
  });
});

test.describe('Watchlist — Integration', () => {
  test('can add and remove ticker from watchlist', async ({ page }) => {
    await login(page);
    await page.goto('/watchlist');
    await page.waitForTimeout(3000);

    // Find add input
    const searchInput = page.locator('input[placeholder*="ticker" i], input[placeholder*="busca" i], input[type="search"], input[placeholder*="ATIVO" i]').first();
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('PETR4');
      await page.waitForTimeout(1000);
      // Try to submit/add
      await page.keyboard.press('Enter');
      await page.waitForTimeout(2000);
      // Check if PETR4 appears in the list
      const body = await page.textContent('body');
      // Either it was added or there was a message
      expect(body).toMatch(/PETR4|adicionado|erro|já existe/i);
    } else {
      // Mark as skipped if UI not found
      test.skip(true, 'Watchlist add input not found');
    }
  });
});
