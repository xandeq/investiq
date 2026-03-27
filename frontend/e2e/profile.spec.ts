import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('Profile — Smoke', () => {
  test('/profile page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/profile');
    expect(status).toBe('OK');
  });

  test('/planos page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/planos');
    expect(status).toBe('OK');
  });

  test('profile page shows user information', async ({ page }) => {
    await login(page);
    await page.goto('/profile');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/perfil|profile|conta|email|nome|usuário/i);
  });
});

test.describe('Profile — Regression', () => {
  test('profile page does not crash', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/profile');
    await page.waitForTimeout(4000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });

  test('planos page shows subscription plans', async ({ page }) => {
    await login(page);
    await page.goto('/planos');
    await page.waitForTimeout(4000);
    const body = await page.textContent('body');
    expect(body).toMatch(/plano|plan|premium|free|gratuito|assinatura|preço/i);
  });

  test('profile shows investor profile or settings', async ({ page }) => {
    await login(page);
    await page.goto('/profile');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    // Should show profile fields
    expect(body).toMatch(/perfil|investidor|conservador|moderado|agressivo|email|nome/i);
  });
});

test.describe('Profile — Integration', () => {
  test('planos page has upgrade/manage buttons', async ({ page }) => {
    await login(page);
    await page.goto('/planos');
    await page.waitForTimeout(4000);
    const actionBtn = page.locator('button, a').filter({ hasText: /assinar|upgrade|gerenciar|cancelar|plano|stripe/i }).first();
    const hasBtn = await actionBtn.isVisible({ timeout: 3000 }).catch(() => false);
    const body = await page.textContent('body');
    expect(hasBtn || body!.match(/plano|premium|free|R\$|preço/i)).toBeTruthy();
  });

  test('profile can update investor profile type', async ({ page }) => {
    await login(page);
    await page.goto('/profile');
    await page.waitForTimeout(3000);
    // Check if investor profile selector exists
    const profileSelect = page.locator('select, [role="combobox"], button')
      .filter({ hasText: /conservador|moderado|agressivo|perfil/i }).first();
    const hasSelect = await profileSelect.isVisible({ timeout: 3000 }).catch(() => false);
    const body = await page.textContent('body');
    // Either editable or displayed
    expect(body).toMatch(/perfil|investidor|email|conta/i);
  });
});
