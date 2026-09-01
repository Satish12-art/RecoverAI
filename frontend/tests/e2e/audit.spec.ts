import { test, expect } from "@playwright/test";

test.describe("Audit Trail & Policy Guardrails", () => {
  test("Displays 10 active policy guardrails and audit events table", async ({ page }) => {
    await page.goto("/audit");
    await page.waitForLoadState("networkidle");

    // 1. Policy Guardrails Panel
    await expect(page.getByText("Active Deterministic Policy Guardrails (10 Rules)")).toBeVisible();
    await expect(page.getByText("Rule 1").first()).toBeVisible();
    await expect(page.getByText("Rule 2").first()).toBeVisible();
    await expect(page.getByText("Rule 10").first()).toBeVisible();

    // 2. Audit Table or EmptyState
    const hasTable = await page.locator("table").isVisible().catch(() => false);
    const hasEmptyState = await page.getByText("No Audit Records Found").isVisible().catch(() => false);
    expect(hasTable || hasEmptyState).toBeTruthy();
  });
});
