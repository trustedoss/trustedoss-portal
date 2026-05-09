/**
 * IntegrationsHarness — chore C smoke coverage.
 *
 * Domain verbs for the `/integrations` surface (API keys + webhook copy
 * cards). Mirrors the {@link AuthHarness} pattern: every selector is rooted
 * in a `data-testid` the SPA emits verbatim, never a translated label, so
 * EN / KO renders pass on the same scenarios.
 *
 * Hard rules (CLAUDE.md "품질·보안·운영 표준" §2 + test-writer.md):
 *   - No mocking of our own backend. Real HTTP against docker-compose dev.
 *   - No `page.waitForTimeout()`. Use Playwright auto-retry assertions.
 *   - Selectors live inside the harness; spec files never touch CSS/text.
 *
 * Scope of this harness is intentionally narrow — we cover only the
 * navigation + create-dialog open/close round trip. The actual create +
 * revoke round trip is exercised in unit tests; running it in E2E adds
 * write-flakiness against a live Postgres for negligible additional signal.
 */
import { expect, type Page } from "@playwright/test";

const DEFAULT_BASE_URL = "http://localhost:5173";
const DEFAULT_TIMEOUT_MS = 10_000;

export class IntegrationsHarness {
  readonly page: Page;
  readonly baseUrl: string;

  constructor(page: Page, baseUrl: string = DEFAULT_BASE_URL) {
    this.page = page;
    this.baseUrl = baseUrl;
  }

  // ───── navigation ──────────────────────────────────────────────────────
  async goto(): Promise<void> {
    await this.page.goto(`${this.baseUrl}/integrations`);
    await this.expectMounted();
  }

  // ───── assertions ──────────────────────────────────────────────────────
  /**
   * The `integrations-page` testid wraps the whole route surface (header +
   * API keys section + webhooks section). We also assert the Create button
   * to confirm interactive controls hydrated, not just the SSR shell.
   */
  async expectMounted(): Promise<void> {
    await expect(this.page.getByTestId("integrations-page")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    await expect(this.page.getByTestId("integrations-create-key")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
  }

  // ───── create-dialog round trip ────────────────────────────────────────
  async clickCreate(): Promise<void> {
    await this.page.getByTestId("integrations-create-key").click();
  }

  async expectCreateDialogOpen(): Promise<void> {
    await expect(
      this.page.getByTestId("integrations-create-dialog"),
    ).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
  }

  /**
   * Close the create dialog via Escape (the canonical shadcn affordance)
   * and assert the dialog is gone. Using Escape rather than the cancel
   * button keeps the verb decoupled from the button label and double-checks
   * the keyboard a11y path.
   */
  async closeCreateDialog(): Promise<void> {
    await this.page.keyboard.press("Escape");
    await expect(
      this.page.getByTestId("integrations-create-dialog"),
    ).toHaveCount(0, { timeout: DEFAULT_TIMEOUT_MS });
  }
}
