import { Page } from '@playwright/test';

export const BASE = 'https://investiq.com.br';
export const API = 'https://api.investiq.com.br';
export const TEST_EMAIL = 'playtest@investiq.com.br';
export const TEST_PASSWORD = 'Teste1234!';

export async function login(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').waitFor({ timeout: 10000 });
  await page.getByLabel('Email').fill(TEST_EMAIL);
  await page.locator('#password').fill(TEST_PASSWORD);
  await page.getByRole('button', { name: /entrar/i }).click();
  await page.waitForLoadState('networkidle').catch(() => null);
  const url = page.url();
  const body = await page.locator('body').innerText().catch(() => '');
  console.log(`[LOGIN] Final URL: ${url}`);
  console.log(`[LOGIN] Body preview: ${body.substring(0, 200)}`);
  if (url.includes('login') || body.match(/email ou senha|não verificado/i)) {
    throw new Error(`Login failed - still on login page or auth error. URL: ${url}`);
  }
}

export async function pageIsOk(page: Page, path: string): Promise<string> {
  const response = await page.goto(path);
  await page.waitForLoadState('networkidle').catch(() => null);
  const url = page.url();
  const body = (await page.locator('body').innerText().catch(() => '')) ?? '';
  if (url.includes('login')) return 'REDIRECT_TO_LOGIN';
  if ((response && response.status() >= 400) || url.match(/\/404(?:[/?#]|$)|not-found/i)) return '404';
  if (body.match(/internal server error/i)) return '500';
  if (body.match(/application error/i)) return 'APP_ERROR';
  return 'OK';
}
