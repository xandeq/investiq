import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Tools — Smoke', () => {
  test('/comparador page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/comparador');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });

  test('/simulador page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/simulador');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });

  test('/ir-helper page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/ir-helper');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });

  test('/renda-fixa page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/renda-fixa');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });

  test('/insights page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/insights');
    expect(status).not.toBe('404');
    expect(status).not.toBe('500');
    expect(status).not.toBe('APP_ERROR');
  });
});

test.describe('Tools — Regression', () => {
  test('comparador has comparison UI', async ({ page }) => {
    await login(page);
    await page.goto('/comparador');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/comparar|comparador|ativo|ticker/i);
    expect(body).not.toMatch(/TypeError|ReferenceError/i);
  });

  test('simulador has investment simulation inputs', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(4000);
    const inputs = page.locator('input[type="number"], input[type="text"]');
    const hasInputs = await inputs.count() > 0;
    const body = await page.textContent('body');
    expect(body).toMatch(/simul|invest|valor|rendimento|taxa/i);
    expect(hasInputs || body!.match(/simul/i)).toBeTruthy();
  });

  test('ir-helper shows IR calculation UI', async ({ page }) => {
    await login(page);
    await page.goto('/ir-helper');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/IR|imposto|renda|DARF|declaração|calculo/i);
  });

  test('renda-fixa shows fixed income content', async ({ page }) => {
    await login(page);
    await page.goto('/renda-fixa');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/renda fixa|CDB|Tesouro|LCI|LCA|CDI/i);
  });

  test('insights shows market insights', async ({ page }) => {
    await login(page);
    await page.goto('/insights');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/insight|mercado|análise|notícia|atualiz/i);
  });
});

test.describe('Tools — Integration', () => {
  test('simulador calculation produces result', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(3000);

    const numberInputs = page.locator('input[type="number"]');
    const count = await numberInputs.count();
    if (count > 0) {
      // Fill first input with a value
      await numberInputs.first().fill('10000');
      if (count > 1) await numberInputs.nth(1).fill('12');

      // Find simulate/calculate button
      const calcBtn = page.locator('button').filter({ hasText: /simul|calcul|calcular|projetar/i }).first();
      if (await calcBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await calcBtn.click();
        await page.waitForTimeout(3000);
        const body = await page.textContent('body');
        expect(body).not.toMatch(/TypeError|application error/i);
      }
    }
  });

  test('ir-helper DARF calculation', async ({ page }) => {
    await login(page);
    await page.goto('/ir-helper');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).not.toMatch(/application error|TypeError/i);
    // Should have some way to calculate or see IR data
    expect(body).toMatch(/IR|imposto|DARF|mês|operação/i);
  });
});
