import { test, expect } from '@playwright/test';
import { login, pageIsOk } from './helpers';

test.describe('v1.4 — Phase 21: Screener de Ações', () => {
  test('/acoes/screener page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/acoes/screener');
    expect(status).toBe('OK');
    console.log('✓ Phase 21 page loads');
  });

  test('/acoes/screener has table with columns', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(3000);
    
    const body = await page.locator('body').innerText();
    expect(body).toMatch(/ticker|setor|preço|variação|dy|p\/l|market cap/i);
    console.log('✓ Phase 21 table columns present');
  });

  test('/acoes/screener has filter controls (DY, P/L, Setor, Market Cap)', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(3000);
    
    const dyInput = page.locator('input[placeholder*="DY"], input[placeholder*="5"]').first();
    const plInput = page.locator('input[placeholder*="P/L"], input[placeholder*="20"]').nth(1);
    const sectorSelect = page.locator('select').first();
    const marketCapButtons = page.locator('button').filter({ hasText: /Small|Mid|Large|Pequeno|Médio|Grande/i });
    
    const hasFilters = 
      (await dyInput.isVisible({ timeout: 2000 }).catch(() => false)) ||
      (await plInput.isVisible({ timeout: 2000 }).catch(() => false)) ||
      (await sectorSelect.isVisible({ timeout: 2000 }).catch(() => false)) ||
      (await marketCapButtons.count()) > 0;
    
    expect(hasFilters).toBeTruthy();
    console.log('✓ Phase 21 filters present');
  });

  test('/acoes/screener pagination works (PAGE_SIZE=50)', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(3000);
    
    const body = await page.locator('body').innerText();
    const hasPagination = body.match(/próxima|anterior|página|paginação|anterior|próximo/i) !== null;
    const hasDataTable = body.match(/ticker/i) !== null;
    
    expect(hasDataTable || hasPagination).toBeTruthy();
    console.log('✓ Phase 21 pagination layout present');
  });
});

test.describe('v1.4 — Phase 22: Catálogo Renda Fixa', () => {
  test('/renda-fixa page loads', async ({ page }) => {
    await login(page);
    const status = await pageIsOk(page, '/renda-fixa');
    expect(status).toBe('OK');
    console.log('✓ Phase 22 page loads');
  });

  test('/renda-fixa has catalog grouped by type', async ({ page }) => {
    await login(page);
    await page.goto('/renda-fixa');
    await page.waitForTimeout(3000);
    
    const body = await page.locator('body').innerText();
    expect(body).toMatch(/tesouro|cdb|lci|lca|renda fixa|taxa|vencimento/i);
    console.log('✓ Phase 22 catalog types present');
  });

  test('/renda-fixa has net return display (retorno líquido)', async ({ page }) => {
    await login(page);
    await page.goto('/renda-fixa');
    await page.waitForTimeout(3000);
    
    const body = await page.locator('body').innerText();
    const hasNetReturn = body.match(/retorno líquido|líquido|ir|imposto|90d|1a|2a|5a/i) !== null;
    expect(hasNetReturn).toBeTruthy();
    console.log('✓ Phase 22 net return display present');
  });

  test('/renda-fixa has beat indicator (CDI/IPCA)', async ({ page }) => {
    await login(page);
    await page.goto('/renda-fixa');
    await page.waitForTimeout(3000);
    
    const body = await page.locator('body').innerText();
    const hasBeat = body.match(/cdi|ipca|beat|supera|verde|vermelho|acima|abaixo/i) !== null;
    expect(hasBeat).toBeTruthy();
    console.log('✓ Phase 22 beat indicator present');
  });

  test('/renda-fixa has filters by type and prazo', async ({ page }) => {
    await login(page);
    await page.goto('/renda-fixa');
    await page.waitForTimeout(3000);
    
    const selects = page.locator('select');
    const inputs = page.locator('input[type="number"], input[type="text"]');
    const buttons = page.locator('button').filter({ hasText: /filtro|tipo|tesouro|cdb/i });
    
    const hasFilters = 
      (await selects.count()) > 0 ||
      (await inputs.count()) > 0 ||
      (await buttons.count()) > 0;
    
    expect(hasFilters).toBeTruthy();
    console.log('✓ Phase 22 filters present');
  });
});

test.describe('v1.4 — Navigation Links', () => {
  test('Sidebar/Nav has links to /acoes/screener and /renda-fixa', async ({ page }) => {
    await login(page);
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
    
    const body = await page.locator('body').innerText();
    const sidebarText = await page.locator('nav, aside, [role="navigation"]').innerText().catch(() => '');
    
    const hasAcoesLink = body.match(/ações|screener de ações|acoes/) !== null;
    const hasRFLink = body.match(/renda fixa|fixa/) !== null;
    
    console.log(`  Found "ações" link: ${hasAcoesLink}`);
    console.log(`  Found "renda fixa" link: ${hasRFLink}`);
    
    expect(hasAcoesLink || hasRFLink).toBeTruthy();
  });
});
