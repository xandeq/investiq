/**
 * Regression tests — Phase 38 (Fundos de Investimento)
 *
 * Bug 1: SET LOCAL rls.tenant_id = $1 (asyncpg rejects parameterized SET LOCAL)
 *   Symptom: GET /funds/*, GET /outcomes/stats → 500
 *   Fix: db.py line 44 — use f-string after UUID validation instead of :tid param
 *   Root cause: asyncpg does not support $1 syntax in SET statements
 *
 * Bug 2: Migration 0037 — ALTER TYPE assetclass needs ownership
 *   Symptom: alembic upgrade head fails with InsufficientPrivilegeError
 *   Fix: ALTER TYPE assetclass OWNER TO app_user (run as postgres superuser before migration)
 */
import { test, expect, request as playwrightRequest } from '@playwright/test';

const API = 'https://api.investiq.com.br';

async function getAuthCookie(): Promise<string> {
  const ctx = await playwrightRequest.newContext();
  const r = await ctx.post(`${API}/auth/login`, {
    data: { email: 'playtest@investiq.com.br', password: 'Teste1234!' },
  });
  const cookies = r.headers()['set-cookie'] ?? '';
  const match = cookies.match(/access_token=([^;]+)/);
  await ctx.dispose();
  return match ? match[1] : '';
}

test.describe('Phase 38 Regression — RLS SET LOCAL', () => {
  // Covers bug: SET LOCAL rls.tenant_id = $1 (asyncpg param rejection)
  test('bug: GET /funds/search returns 200 not 500', async ({ request }) => {
    const token = await getAuthCookie();
    const r = await request.get(`${API}/funds/search?q=itau`, {
      headers: { Cookie: `access_token=${token}` },
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('bug: GET /funds/positions returns 200 not 500', async ({ request }) => {
    const token = await getAuthCookie();
    const r = await request.get(`${API}/funds/positions`, {
      headers: { Cookie: `access_token=${token}` },
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('bug: GET /outcomes/stats returns 200 not 500', async ({ request }) => {
    const token = await getAuthCookie();
    const r = await request.get(`${API}/outcomes/stats`, {
      headers: { Cookie: `access_token=${token}` },
    });
    expect(r.status()).toBe(200);
  });

  test('feature: funds endpoints are protected (401 without auth)', async ({ request }) => {
    for (const path of ['/funds/search?q=x', '/funds/positions']) {
      const r = await request.get(`${API}${path}`);
      expect(r.status()).toBeGreaterThanOrEqual(401);
      expect(r.status()).toBeLessThan(500);
    }
  });

  test('feature: GET /funds/info/{cnpj} returns 404 for unknown CNPJ', async ({ request }) => {
    const token = await getAuthCookie();
    const r = await request.get(`${API}/funds/info/00000000000000`, {
      headers: { Cookie: `access_token=${token}` },
    });
    expect(r.status()).toBe(404);
  });
});
