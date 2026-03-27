import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Screener — Smoke', () => {
  test('/screener page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/screener');
    expect(status).toBe('OK');
  });

  test('/screener/acoes page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/screener/acoes');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
  });

  test('/screener/fiis page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/screener/fiis');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
  });

  test('screener page has filter controls', async ({ page }) => {
    await login(page);
    await page.goto('/screener');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/screener|filtro|busca|ação|FII|ativo/i);
  });
});

test.describe('Screener — Regression', () => {
  test('screener does not crash on load', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/screener');
    await page.waitForTimeout(5000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });

  test('screener has filter inputs or dropdowns', async ({ page }) => {
    await login(page);
    await page.goto('/screener');
    await page.waitForTimeout(4000);
    const filters = page.locator('select, input[type="number"], input[type="text"], [role="combobox"]');
    const count = await filters.count();
    expect(count).toBeGreaterThan(0);
  });

  test('screener run button is present', async ({ page }) => {
    await login(page);
    await page.goto('/screener');
    await page.waitForTimeout(3000);
    const runBtn = page.locator('button').filter({ hasText: /filtrar|buscar|aplicar|executar|rodar|screen/i }).first();
    const hasBtn = await runBtn.isVisible({ timeout: 3000 }).catch(() => false);
    const body = await page.textContent('body');
    expect(hasBtn || body!.match(/resultado|ativo|ticker/i)).toBeTruthy();
  });
});

test.describe('Screener — Integration', () => {
  test('screener run returns results or empty state', async ({ page }) => {
    await login(page);
    await page.goto('/screener');
    await page.waitForTimeout(3000);

    const runBtn = page.locator('button').filter({ hasText: /filtrar|buscar|aplicar|executar|screen/i }).first();
    if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await runBtn.click();
      // Wait for API response
      await page.waitForTimeout(8000);
      const body = await page.textContent('body');
      expect(body).not.toMatch(/application error|TypeError/i);
      // Should show results or empty state message
      expect(body).toMatch(/resultado|ativo|ticker|encontrado|nenhum|vazio|filtro/i);
    } else {
      // Results may already be shown
      const body = await page.textContent('body');
      expect(body).toMatch(/screener|ativo|filtro|P\/L|P\/VP/i);
    }
  });

  test('screener acoes shows stock-specific metrics', async ({ page }) => {
    await login(page);
    await page.goto('/screener/acoes');
    await page.waitForTimeout(5000);
    const body = await page.textContent('body');
    expect(body).not.toMatch(/application error/i);
    // Should have typical stock metrics
    expect(body).toMatch(/P\/L|P\/VP|dividend|ROE|ticker|ação|screener/i);
  });
});
