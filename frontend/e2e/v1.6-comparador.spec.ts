import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('v1.6 — Phase 27: Comparador RF vs RV', () => {
  test('/comparador page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/comparador');
    expect(status).toBe('OK');
  });

  test('/comparador form + 4-row table visible', async ({ page }) => {
    await login(page);
    await page.goto('/comparador');
    await page.waitForTimeout(3000);

    const body = await page.locator('body').innerText();
    // Table columns (per D-08)
    expect(body).toMatch(/Taxa Bruta/i);
    expect(body).toMatch(/Taxa Líquida/i);
    expect(body).toMatch(/Retorno Nominal/i);
    expect(body).toMatch(/Retorno Real/i);
    expect(body).toMatch(/Total Acumulado/i);
    // Four benchmark rows (produto_rf label + CDI + SELIC + IPCA+)
    expect(body).toMatch(/CDI/);
    expect(body).toMatch(/SELIC/);
    expect(body).toMatch(/IPCA/);
  });

  test('/comparador shows chart section (COMP-02)', async ({ page }) => {
    await login(page);
    await page.goto('/comparador');
    await page.waitForTimeout(3000);

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/Evolução do patrimônio/i);

    // Recharts renders an <svg class="recharts-surface">
    const svg = page.locator('svg.recharts-surface').first();
    await expect(svg).toBeVisible({ timeout: 5000 });
  });

  test('/comparador Tesouro IPCA+ exposes spread input (COMP-01 / D-16)', async ({ page }) => {
    await login(page);
    await page.goto('/comparador');
    await page.waitForTimeout(2500);

    // Select the tipo RF dropdown and change to TESOURO_IPCA
    const tipoSelect = page.locator('select').first();
    await tipoSelect.selectOption('TESOURO_IPCA');
    await page.waitForTimeout(500);

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/Spread/i);
  });
});
