/**
 * AdminDTHarness — Phase 4 PR #14 §4.4.
 *
 * Domain verbs for the ``/admin/dt`` surface. Sibling of
 * {@link AdminUsersHarness}: every selector is a ``data-testid`` /
 * ``data-*`` attribute, never a translated label, so EN/KO renders
 * pass on the same scenarios.
 */
import { expect, type Page } from "@playwright/test";

const DEFAULT_BASE_URL = "http://localhost:5173";
const DEFAULT_TIMEOUT_MS = 10_000;

export type DTBreakerState = "closed" | "open" | "half_open";
export type DTBreakerTone = "ok" | "degraded" | "down";
export type DTSuccessKey = "health_checked" | "cleanup_enqueued";
export type DTErrorExtension =
  | "dt_unreachable"
  | "dt_orphan_cleanup_in_progress";

export class AdminDTHarness {
  readonly page: Page;
  readonly baseUrl: string;

  constructor(page: Page, baseUrl: string = DEFAULT_BASE_URL) {
    this.page = page;
    this.baseUrl = baseUrl;
  }

  // ───── navigation ──────────────────────────────────────────────────────
  async goto(): Promise<void> {
    await this.page.goto(`${this.baseUrl}/admin/dt`);
    await this.expectMounted();
  }

  async expectMounted(): Promise<void> {
    await expect(this.page.getByTestId("admin-layout")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    await expect(this.page.getByTestId("admin-dt-page")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    // Wait until the status card finishes its initial fetch — the badge
    // only mounts after the query resolves so its presence is the signal.
    await expect(this.page.getByTestId("dt-breaker-badge")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
  }

  async expectAccessDenied(): Promise<void> {
    await expect(this.page.getByTestId("admin-not-found")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    await expect(this.page.getByTestId("admin-layout")).toHaveCount(0);
  }

  // ───── status card ─────────────────────────────────────────────────────
  /** Read the breaker state via ``data-state`` attribute. */
  async getBreakerState(): Promise<DTBreakerState | null> {
    const value = await this.page
      .getByTestId("dt-breaker-badge")
      .getAttribute("data-state");
    return value === null ? null : (value as DTBreakerState);
  }

  /** Read the colour-tone classification (ok / degraded / down). */
  async getBreakerTone(): Promise<DTBreakerTone | null> {
    const value = await this.page
      .getByTestId("dt-breaker-badge")
      .getAttribute("data-tone");
    return value === null ? null : (value as DTBreakerTone);
  }

  async forceHealthProbe(): Promise<void> {
    await this.page.getByTestId("admin-dt-force-probe").click();
  }

  // ───── orphan list ─────────────────────────────────────────────────────
  async expectOrphanRow(uuid: string): Promise<void> {
    await expect(
      this.page.locator(
        `[data-testid="admin-dt-orphan-row"][data-uuid="${cssEscape(uuid)}"]`,
      ),
    ).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
  }

  async toggleOrphanCheckbox(uuid: string): Promise<void> {
    await this.page
      .locator(
        `[data-testid="admin-dt-orphan-checkbox"][data-uuid="${cssEscape(uuid)}"]`,
      )
      .click();
  }

  async cleanupAll(): Promise<void> {
    await this.page.getByTestId("admin-dt-cleanup-all").click();
    await expect(this.page.getByTestId("admin-dt-confirm-strip")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    await this.page.getByTestId("admin-dt-confirm-ok").click();
  }

  async cleanupSelected(): Promise<void> {
    await this.page.getByTestId("admin-dt-cleanup-selected").click();
    await expect(this.page.getByTestId("admin-dt-confirm-strip")).toBeVisible({
      timeout: DEFAULT_TIMEOUT_MS,
    });
    await this.page.getByTestId("admin-dt-confirm-ok").click();
  }

  // ───── toast assertions ────────────────────────────────────────────────
  async expectSuccessToast(key: DTSuccessKey): Promise<void> {
    await expect(
      this.page.locator(
        `[data-testid="admin-toast"][data-tone="success"][data-toast-key="${key}"]`,
      ),
    ).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
  }

  async expectErrorAlert(extension: DTErrorExtension): Promise<void> {
    await expect(
      this.page.locator(
        `[data-testid="admin-toast"][data-tone="error"][data-toast-key="${extension}"]`,
      ),
    ).toBeVisible({ timeout: DEFAULT_TIMEOUT_MS });
  }
}

function cssEscape(value: string): string {
  return value.replace(/(["\\])/g, "\\$1");
}
