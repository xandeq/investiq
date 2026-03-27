import { Page, expect } from '@playwright/test';

export const BASE = 'https://investiq.com.br';
export const API  = 'https://api.investiq.com.br';
export const TEST_EMAIL    = 'playtest@investiq.com.br';
export const TEST_PASSWORD = 'Teste1234!';

export async function login(page: Page) {
  await page.goto('/login');
  await page.waitForSelector('input[type="email"]', { timeout: 10000 });
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard|portfolio|\/app/, { timeout: 15000 });
}

export async function pageIsOk(page: Page, path: string): Promise<string> {
  await page.goto(path);
  await page.waitForTimeout(3000);
  const url  = page.url();
  const body = (await page.textContent('body')) ?? '';
  if (url.includes('login'))                 return 'REDIRECT_TO_LOGIN';
  if (url.match(/404|not.found/i))           return '404';
  if (body.match(/internal server error/i))  return '500';
  if (body.match(/application error/i))      return 'APP_ERROR';
  return 'OK';
}
