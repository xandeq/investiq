import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('v1.7 — Phase 28: Simulador de Alocação', () => {
  test('/simulador page loads (200)', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/simulador');
    expect(status).toBe('OK');
  });

  test('/simulador renders 3 scenario labels (SIM-01)', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(3000);

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/Conservador/);
    expect(body).toMatch(/Moderado/);
    expect(body).toMatch(/Arrojado/);
  });

  test('/simulador shows per-class projections (SIM-02)', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(3000);

    const body = await page.locator('body').innerText();
    // Each scenario card renders RF / Ações / FIIs breakdown rows.
    expect(body).toMatch(/Renda Fixa|RF/i);
    expect(body).toMatch(/Ações/i);
    expect(body).toMatch(/FIIs/i);
    // At least one BRL-formatted amount (R$ X.XXX,XX) from the projections.
    expect(body).toMatch(/R\$\s*[\d.,]+/);
  });

  test('/simulador form inputs update scenarios live (SIM-01 / SIM-02)', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(3000);

    // Change valor input and verify the page still renders scenarios (no reload, no error).
    const valorInput = page.locator('input[type="number"]').first();
    await valorInput.fill('50000');
    await page.waitForTimeout(1000);

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/Conservador/);
    expect(body).toMatch(/R\$\s*[\d.,]+/);
  });

  test('/simulador delta section renders (SIM-03 — either CTA or delta rows)', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(4000); // allow advisor/health + portfolio/pnl to settle

    const body = await page.locator('body').innerText();
    // Delta section header always renders
    expect(body).toMatch(/Delta vs carteira atual/i);
    // Either the no-portfolio CTA or the delta action labels must be present.
    const hasCTA = /Cadastrar transações/i.test(body);
    const hasDeltaActions = /Comprar|Reduzir|Manter/.test(body);
    expect(hasCTA || hasDeltaActions).toBeTruthy();
  });

  test('/simulador CVM disclaimer visible', async ({ page }) => {
    await login(page);
    await page.goto('/simulador');
    await page.waitForTimeout(2500);

    const body = await page.locator('body').innerText();
    expect(body).toMatch(/não constitui recomendação/i);
  });
});
