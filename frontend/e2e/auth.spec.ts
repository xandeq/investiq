import { test, expect } from '@playwright/test';
import { login, TEST_EMAIL } from './helpers';

test.describe('Auth - Smoke', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByLabel('Email')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.getByRole('button', { name: /entrar/i })).toBeVisible();
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByLabel('Email')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('#confirmPassword')).toBeVisible();
  });

  test('unauthenticated access to dashboard redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForURL(/login|auth/, { timeout: 15000 });
    expect(page.url()).toMatch(/login|auth/);
  });
});

test.describe('Auth - Regression', () => {
  test('wrong password shows error message', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').waitFor({ timeout: 10000 });
    await page.getByLabel('Email').fill(TEST_EMAIL);
    await page.locator('#password').fill('wrongpassword123');
    await page.getByRole('button', { name: /entrar/i }).click();
    await expect(page).toHaveURL(/login/, { timeout: 10000 });
    await expect(page.getByText(/email ou senha incorretos/i)).toBeVisible({ timeout: 10000 });
  });

  test('login with valid credentials succeeds', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/dashboard|portfolio|\/app/, { timeout: 15000 });
  });
});

test.describe('Auth - Integration', () => {
  test('full login + logout flow', async ({ page }) => {
    await login(page);
    await expect(page.getByRole('navigation')).toBeVisible({ timeout: 10000 });

    const logoutBtn = page.getByRole('button', { name: /sair/i });
    await expect(logoutBtn).toBeVisible({ timeout: 10000 });
    await Promise.all([
      page.waitForURL(/login/, { timeout: 15000 }),
      logoutBtn.click(),
    ]);

    await page.goto('/dashboard');
    await expect(page).toHaveURL(/login|auth/, { timeout: 10000 });
  });

  test('password reset page is accessible', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.getByLabel('Email')).toBeVisible({ timeout: 10000 });
  });
});
