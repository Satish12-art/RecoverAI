import { test, expect } from "@playwright/test";

test.describe("App Shell Navigation", () => {
  test("Navigates seamlessly across all 5 main pages via sidebar", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 1. Recovery Cases
    await page.click('aside a[href="/cases"]');
    await expect(page).toHaveURL(/\/cases/);
    await expect(page.locator("h2")).toContainText("Recovery Cases");

    // 2. Analytics
    await page.click('aside a[href="/analytics"]');
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.locator("h2")).toContainText("Analytics");

    // 3. Evaluation
    await page.click('aside a[href="/evaluation"]');
    await expect(page).toHaveURL(/\/evaluation/);
    await expect(page.locator("h2")).toContainText("RecoverAI Benchmark Evaluation");

    // 4. Audit Trail
    await page.click('aside a[href="/audit"]');
    await expect(page).toHaveURL(/\/audit/);
    await expect(page.locator("h2")).toContainText("Audit Trail");

    // 5. Return to Dashboard
    await page.click('aside a[href="/"]');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByText("Three-Tier Revenue Hierarchy")).toBeVisible();
  });
});
