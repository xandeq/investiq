import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

// ---------------------------------------------------------------------------
// FII Detail Page — /fii/[ticker]
// ---------------------------------------------------------------------------

test.describe('FII Detail - Smoke', () => {
  test('unauthenticated user is redirected to login', async ({ page }) => {
    const status = await pageIsOk(page, '/fii/HGLG11');
    expect(status).toBe('REDIRECT_TO_LOGIN');
  });

  test('authenticated user: /fii/HGLG11 loads without error', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/fii/HGLG11');
    expect(status).toBe('OK');
  });

  test('no critical JS errors on page load', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/fii/HGLG11');
    await page.waitForTimeout(5000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('FII Detail - UI Elements', () => {
  test('"Gerar Analise IA" button is present', async ({ page }) => {
    await login(page);
    await page.goto('/fii/HGLG11');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const button = page.locator('button:has-text("Gerar Analise IA")');
    await expect(button).toBeVisible({ timeout: 10000 });
  });

  test('"Voltar ao Screener" link navigates to /fii/screener', async ({ page }) => {
    await login(page);
    await page.goto('/fii/HGLG11');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const link = page.locator('a:has-text("Voltar ao Screener")');
    await expect(link).toBeVisible({ timeout: 10000 });
    await link.click();
    await page.waitForURL('**/fii/screener', { timeout: 10000 });
    expect(page.url()).toContain('/fii/screener');
  });

  test('ticker HGLG11 appears in the page heading', async ({ page }) => {
    await login(page);
    await page.goto('/fii/HGLG11');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const heading = page.locator('h1').filter({ hasText: /HGLG11/i }).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });
});

test.describe('FII Detail - CVM Disclaimer Regression', () => {
  test('CVM disclaimer visible after analysis completes', async ({ page }) => {
    test.setTimeout(120_000);
    await login(page);
    await page.goto('/fii/HGLG11');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);

    // Trigger analysis
    const button = page.locator('button:has-text("Gerar Analise IA")');
    if (await button.isVisible()) {
      await button.click();
      // Wait for analysis to complete (up to 90s)
      await page.waitForTimeout(5000);
      // Check for disclaimer text (CVM warning)
      const disclaimer = page.locator('[data-testid="cvm-disclaimer"]').or(
        page.getByText(/recomenda.*investimento/i)
      );
      // Disclaimer appears after analysis completes or may already be visible
      await expect(disclaimer).toBeVisible({ timeout: 90000 });
    }
  });
});
