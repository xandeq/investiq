import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('AI Features — Smoke', () => {
  test('/ai page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/ai');
    expect(status).toBe('OK');
  });

  test('/ai/advisor page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/ai/advisor');
    expect(status).toBe('OK');
  });

  test('/ai page shows analysis options', async ({ page }) => {
    await login(page);
    await page.goto('/ai');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/análise|anális|IA|inteligência|advisor|carteira/i);
  });
});

test.describe('AI Features — Regression', () => {
  test('/ai page has submit button or analysis triggers', async ({ page }) => {
    await login(page);
    await page.goto('/ai');
    await page.waitForTimeout(3000);
    const submitBtn = page.locator('button').filter({ hasText: /analis|gerar|executar|iniciar|solicitar/i }).first();
    const hasBtn = await submitBtn.isVisible({ timeout: 3000 }).catch(() => false);
    const body = await page.textContent('body');
    // Either a button exists or the page shows premium gate / content
    expect(hasBtn || body!.match(/premium|pro|upgrade|carteira|ativo/i)).toBeTruthy();
  });

  test('/ai/advisor shows advisor content or premium gate', async ({ page }) => {
    await login(page);
    await page.goto('/ai/advisor');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/advisor|conselheiro|carteira|anális|premium|pro/i);
  });

  test('/ai page does not show JS errors', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/ai');
    await page.waitForTimeout(4000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('AI Features — Integration', () => {
  test('submit AI portfolio analysis and poll for result', async ({ page }) => {
    await login(page);
    await page.goto('/ai/advisor');
    await page.waitForTimeout(3000);

    const analyzeBtn = page.locator('button').filter({ hasText: /analis|gerar análise|iniciar/i }).first();
    if (await analyzeBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await analyzeBtn.click();
      // Wait for processing indicator or result
      await page.waitForTimeout(5000);
      const body = await page.textContent('body');
      // Should show processing, result, or error — not crash
      expect(body).not.toMatch(/application error|TypeError/i);
      expect(body).toMatch(/analis|processando|resultado|aguarde|carteira|recomend/i);
    } else {
      // Premium gate or no positions — acceptable
      const body = await page.textContent('body');
      expect(body).toMatch(/advisor|anális|premium|carteira|posição/i);
    }
  });

  test('AI macro analysis page is accessible', async ({ page }) => {
    await login(page);
    await page.goto('/ai');
    await page.waitForTimeout(3000);
    // Look for macro tab/section
    const macroTab = page.locator('[role="tab"], button').filter({ hasText: /macro|economia|mercado/i }).first();
    if (await macroTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await macroTab.click();
      await page.waitForTimeout(3000);
      const body = await page.textContent('body');
      expect(body).not.toMatch(/application error/i);
    } else {
      // Macro may be part of main AI page content
      const body = await page.textContent('body');
      expect(body).toMatch(/anális|IA|mercado|carteira/i);
    }
  });
});
