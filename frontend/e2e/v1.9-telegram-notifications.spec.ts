import { test, expect } from '@playwright/test';
import { login } from './helpers';

/**
 * Phase 39 E2E — Telegram notifications (TG-01 connect/persist, TG-03 disconnect).
 *
 * Pre-condition: test user playtest@investiq.com.br has plan="pro" in the test environment.
 * If the test fails with REQUIRES_PRO, verify the test account's plan in the staging DB.
 */

const TEST_CHAT_ID = '721438452';

test.describe('Phase 39 — Telegram Notifications', () => {
  test('connect, persist across reload, disconnect', async ({ page }) => {
    // Step 1: Login + navigate
    await login(page);
    await page.goto('/profile');

    // Step 2: Card visible
    const card = page.getByTestId('telegram-card');
    await expect(card).toBeVisible({ timeout: 10_000 });

    // Step 3: Re-run safety — if already connected from previous run, disconnect first
    const connectedBlock = page.getByTestId('telegram-connected');
    if (await connectedBlock.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await page.getByTestId('telegram-disconnect-btn').click();
      await expect(page.getByTestId('telegram-disconnected')).toBeVisible({ timeout: 5_000 });
    }

    // Step 4: Type chat_id and click Conectar (TG-01)
    await expect(page.getByTestId('telegram-disconnected')).toBeVisible();
    await page.getByTestId('telegram-chat-id-input').fill(TEST_CHAT_ID);
    await page.getByTestId('telegram-connect-btn').click();

    // Step 5: Connected state appears
    await expect(page.getByTestId('telegram-connected')).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText(/Recebendo alertas no chat/)).toBeVisible();

    // Step 6: Reload — persistence check (TG-01)
    await page.reload();
    await expect(page.getByTestId('telegram-card')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId('telegram-connected')).toBeVisible({ timeout: 8_000 });

    // Step 7: Disconnect (TG-03)
    await page.getByTestId('telegram-disconnect-btn').click();
    await expect(page.getByTestId('telegram-disconnected')).toBeVisible({ timeout: 5_000 });
  });

  test('instructions for obtaining chat_id are visible when disconnected', async ({ page }) => {
    await login(page);
    await page.goto('/profile');

    // Ensure disconnected state (cleanup from previous test if needed)
    const connectedBlock = page.getByTestId('telegram-connected');
    if (await connectedBlock.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await page.getByTestId('telegram-disconnect-btn').click();
      await expect(page.getByTestId('telegram-disconnected')).toBeVisible({ timeout: 5_000 });
    }

    // @userinfobot instruction must be present
    await expect(page.getByText(/@userinfobot/)).toBeVisible();
    await expect(page.getByTestId('telegram-chat-id-input')).toBeVisible();
  });

  test('invalid chat_id format shows client-side error', async ({ page }) => {
    await login(page);
    await page.goto('/profile');

    // Ensure disconnected
    const connectedBlock = page.getByTestId('telegram-connected');
    if (await connectedBlock.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await page.getByTestId('telegram-disconnect-btn').click();
      await expect(page.getByTestId('telegram-disconnected')).toBeVisible({ timeout: 5_000 });
    }

    // Type invalid value
    await page.getByTestId('telegram-chat-id-input').fill('abc123def');
    await page.getByTestId('telegram-connect-btn').click();

    // Client-side validation rejects before hitting the server
    await expect(page.getByTestId('telegram-client-error')).toBeVisible({ timeout: 2_000 });
  });
});
