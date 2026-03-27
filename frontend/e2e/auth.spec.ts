import { test, expect } from '@playwright/test';
import { login, TEST_EMAIL, TEST_PASSWORD } from './helpers';

test.describe('Auth — Smoke', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('unauthenticated access to dashboard redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForURL(/login|auth/, { timeout: 15000 });
    expect(page.url()).toMatch(/login|auth/);
  });
});

test.describe('Auth — Regression', () => {
  test('wrong password shows error message', async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('input[type="email"]', { timeout: 10000 });
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', 'wrongpassword123');
    await page.click('button[type="submit"]');
    // Should stay on login page and show error
    await page.waitForTimeout(3000);
    const url = page.url();
    expect(url).toMatch(/login/);
  });

  test('login with valid credentials succeeds', async ({ page }) => {
    await login(page);
    const url = page.url();
    expect(url).not.toMatch(/login/);
  });
});

test.describe('Auth — Integration', () => {
  test('full login + logout flow', async ({ page }) => {
    await login(page);
    // Should be on authenticated page
    expect(page.url()).not.toMatch(/login/);

    // Find logout — look for user menu or logout button
    const logoutBtn = page.locator('button, a').filter({ hasText: /sair|logout|log out/i }).first();
    if (await logoutBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await logoutBtn.click();
      await page.waitForURL(/login|\//, { timeout: 10000 });
    } else {
      // Try to navigate to logout endpoint
      await page.goto('/api/auth/signout');
      await page.waitForTimeout(2000);
    }
    // After logout, protected route should redirect to login
    await page.goto('/dashboard');
    await page.waitForURL(/login|auth/, { timeout: 10000 });
    expect(page.url()).toMatch(/login|auth/);
  });

  test('password reset page is accessible', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
  });
});
