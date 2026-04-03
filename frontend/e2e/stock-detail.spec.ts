import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

// ---------------------------------------------------------------------------
// Stock Detail Page — /stock/[ticker]
// ---------------------------------------------------------------------------

test.describe('Stock Detail — Smoke', () => {
  test('unauthenticated user is redirected to login', async ({ page }) => {
    const status = await pageIsOk(page, '/stock/PETR4');
    expect(status).toBe('REDIRECT_TO_LOGIN');
  });

  test('authenticated user: /stock/PETR4 loads without error', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/stock/PETR4');
    expect(status).toBe('OK');
  });

  test('no critical JS errors on page load', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/stock/PETR4');
    await page.waitForTimeout(5000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Stock Detail — Regression', () => {
  test('disclaimer is visible on page', async ({ page }) => {
    await login(page);
    await page.goto('/stock/PETR4');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const disclaimer = page.getByText(/recomenda.*investimento/i);
    await expect(disclaimer).toBeVisible({ timeout: 10000 });
  });

  test('analysis section headings are visible', async ({ page }) => {
    await login(page);
    await page.goto('/stock/PETR4');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(5000);
    const body = await page.textContent('body');
    // Sections render as loading skeletons ("Calculando...") or completed headings
    expect(body).toMatch(/DCF|Valuation|Lucros|Dividendos|Setorial|Calculando/i);
  });

  test('ticker PETR4 appears in the page heading', async ({ page }) => {
    await login(page);
    await page.goto('/stock/PETR4');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const heading = page.locator('h1').filter({ hasText: /PETR4/i }).first();
    await expect(heading).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Stock Detail — Mobile', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('disclaimer is visible on mobile (375px)', async ({ page }) => {
    await login(page);
    await page.goto('/stock/PETR4');
    await page.waitForLoadState('networkidle').catch(() => null);
    await page.waitForTimeout(3000);
    const disclaimer = page.getByText(/recomenda.*investimento/i);
    await expect(disclaimer).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Stock Detail — Integration', () => {
  test('spinner shows then content or error renders (no crash)', async ({ page }) => {
    test.setTimeout(120_000);

    await login(page);
    await page.goto('/stock/PETR4');

    // Give the analysis pipeline time to start and respond
    await page.waitForTimeout(8000);

    const body = await page.textContent('body');

    // Must not crash with application-level errors
    expect(body).not.toMatch(/application error|TypeError|Unhandled/i);

    // Must show either loading state, completed sections, premium gate, or quota message
    expect(body).toMatch(
      /Calculando|Valuation|Lucros|Dividendos|Setorial|premium|upgrade|Limite de análises|Análise Fundamentalista/i
    );
  });
});
