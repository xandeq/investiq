import { test, expect } from '@playwright/test';
import { login } from './helpers';

test('capture full JS error stack trace', async ({ page }) => {
  const jsErrors: Array<{message: string, stack: string}> = [];
  page.on('pageerror', err => {
    jsErrors.push({ message: err.message, stack: err.stack ?? '' });
    console.log(`[JSERROR] ${err.message}`);
    console.log(`[STACK] ${err.stack?.substring(0, 500)}`);
  });

  // Also capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[CONSOLE ERROR] ${msg.text()}`);
    }
  });

  await login(page);
  await page.goto('/dashboard');
  await page.waitForTimeout(5000);

  console.log(`Total JS errors: ${jsErrors.length}`);
  jsErrors.forEach((e, i) => {
    console.log(`\n--- Error ${i+1} ---`);
    console.log('Message:', e.message);
    console.log('Stack:', e.stack.substring(0, 1000));
  });

  // Just collect, don't fail
  expect(jsErrors.length).toBeGreaterThanOrEqual(0);
});
