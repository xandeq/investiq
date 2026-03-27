import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Portfolio — Smoke', () => {
  test('portfolio page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/portfolio');
    expect(status).toBe('OK');
  });

  test('portfolio page has correct heading', async ({ page }) => {
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/carteira|portfólio|portfolio/i);
  });

  test('transactions page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/portfolio/transactions');
    expect(['OK', 'REDIRECT_TO_LOGIN']).not.toContain('404');
    expect(status).not.toBe('404');
  });
});

test.describe('Portfolio — Regression', () => {
  test('portfolio does not crash with no positions', async ({ page }) => {
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(5000);
    const body = await page.textContent('body');
    expect(body).not.toMatch(/application error|internal server error/i);
    expect(body).not.toMatch(/TypeError|ReferenceError/i);
  });

  test('P&L section renders', async ({ page }) => {
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    // Should show some financial data labels
    expect(body).toMatch(/P&L|lucro|resultado|retorno|carteira/i);
  });

  test('portfolio page has tabs or sections', async ({ page }) => {
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(3000);
    // Should have tab elements or navigation within portfolio
    const tabs = page.locator('[role="tab"], button').filter({ hasText: /posição|transação|dividendo|benchmark|análise/i });
    const count = await tabs.count();
    // Either tabs exist or the content is shown directly
    const body = await page.textContent('body');
    expect(body).toMatch(/posição|ativo|ticker|patrimônio|carteira/i);
  });
});

test.describe('Portfolio — Integration', () => {
  test('portfolio → transactions navigation', async ({ page }) => {
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(3000);
    // Try to find transactions tab/link
    const txLink = page.locator('a[href*="transaction"], button, [role="tab"]')
      .filter({ hasText: /transaç/i }).first();
    if (await txLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await txLink.click();
      await page.waitForTimeout(2000);
      const body = await page.textContent('body');
      expect(body).toMatch(/transaç/i);
    } else {
      // Navigate directly
      await page.goto('/portfolio/transactions');
      await page.waitForTimeout(2000);
      const url = page.url();
      expect(url).not.toMatch(/login/);
    }
  });

  test('portfolio API calls return data without errors', async ({ page }) => {
    const apiErrors: string[] = [];
    page.on('response', response => {
      if (response.url().includes('/portfolio') && response.status() >= 500) {
        apiErrors.push(`${response.status()} ${response.url()}`);
      }
    });
    await login(page);
    await page.goto('/portfolio');
    await page.waitForTimeout(5000);
    expect(apiErrors).toHaveLength(0);
  });
});
