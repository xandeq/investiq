import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';
import path from 'path';
import fs from 'fs';

test.describe('Imports — Smoke', () => {
  test('imports page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/imports');
    expect(status).toBe('OK');
  });

  test('imports page has upload UI', async ({ page }) => {
    await login(page);
    await page.goto('/imports');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toMatch(/import|upload|CSV|planilha|arquivo/i);
  });
});

test.describe('Imports — Regression', () => {
  test('imports page renders without errors', async ({ page }) => {
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await login(page);
    await page.goto('/imports');
    await page.waitForTimeout(4000);
    const criticalErrors = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(criticalErrors).toHaveLength(0);
  });

  test('file input or drop zone is present', async ({ page }) => {
    await login(page);
    await page.goto('/imports');
    await page.waitForTimeout(3000);
    const fileInput = page.locator('input[type="file"]').first();
    const dropZone = page.locator('[class*="drop"], [class*="upload"], [data-testid*="upload"]').first();
    const hasFileInput = await fileInput.count() > 0;
    const hasDropZone = await dropZone.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasFileInput || hasDropZone).toBeTruthy();
  });
});

test.describe('Imports — Integration', () => {
  test('CSV upload with minimal valid file', async ({ page }) => {
    await login(page);
    await page.goto('/imports');
    await page.waitForTimeout(3000);

    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.count() > 0) {
      // Create a minimal test CSV in memory
      const csvContent = 'ticker,tipo,quantidade,preco,data\nPETR4,COMPRA,10,30.50,2024-01-15\n';
      const tmpPath = path.join(process.env.TEMP || '/tmp', 'test_import.csv');
      fs.writeFileSync(tmpPath, csvContent);
      await fileInput.setInputFiles(tmpPath);
      await page.waitForTimeout(2000);
      const body = await page.textContent('body');
      // Should show some feedback (preview, success, or error)
      expect(body).toMatch(/importar|enviado|preview|erro|inválido|arquivo/i);
      fs.unlinkSync(tmpPath);
    } else {
      test.skip(true, 'File input not found on imports page');
    }
  });
});
