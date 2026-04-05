import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Wizard - Smoke', () => {
  test('/wizard page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/wizard');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });

  test('wizard page has form or questions', async ({ page }) => {
    await login(page);
    await page.goto('/wizard');
    await page.waitForTimeout(3000);
    const body = await page.locator('body').innerText();
    expect(body).toMatch(/invest|wizard|onde|perfil|objetivo|risco/i);
  });
});

test.describe('Wizard - Regression', () => {
  test('wizard does not crash on load', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/wizard');
    await page.waitForTimeout(4000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });

  test('wizard has navigation buttons or steps', async ({ page }) => {
    await login(page);
    await page.goto('/wizard');
    await page.waitForTimeout(3000);
    const body = await page.locator('body').innerText();
    const nextBtn = page.locator('button').filter({ hasText: /proximo|continuar|avancar|next|comecar|analisar/i }).first();
    const hasBtn = await nextBtn.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasBtn || body.match(/passo|etapa|step|pergunta|invest/i)).toBeTruthy();
  });
});

test.describe('Wizard - Integration', () => {
  test('wizard completes first step', async ({ page }) => {
    await login(page);
    await page.goto('/wizard');
    await page.waitForTimeout(3000);

    const nextBtn = page.locator('button').filter({ hasText: /proximo|continuar|avancar|next|comecar|analisar/i }).first();
    if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      const firstOption = page.locator('button[data-value], [role="radio"], input[type="radio"]').first();
      if (await firstOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstOption.click();
        await page.waitForTimeout(500);
      }
      await nextBtn.click();
      await page.waitForTimeout(2000);
      const body = await page.locator('body').innerText();
      expect(body).not.toMatch(/application error|TypeError/i);
    }

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/invest|perfil|objetivo|risco|ativo/i);
  });
});
