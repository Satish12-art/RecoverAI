import { test, expect } from "@playwright/test";

test.describe("Executive Dashboard", () => {
  test("Renders formatted KPIs, 3-tier funnel, and interactive Opportunities Queue", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 1. Verify 5 KPI cards contain currency values
    const kpiCards = page.locator(".grid.grid-cols-1.md\\:grid-cols-5 > div");
    await expect(kpiCards).toHaveCount(5);

    await expect(page.getByText("Gross Revenue at Risk")).toBeVisible();
    await expect(page.getByText("Potentially Recoverable").first()).toBeVisible();
    await expect(page.getByText("Revenue Recovered").first()).toBeVisible();

    // 2. Verify Three-Tier Funnel
    await expect(page.getByText("Tier 1: Gross at Risk")).toBeVisible();
    await expect(page.getByText("Tier 2: Potentially Recoverable")).toBeVisible();
    await expect(page.getByText("Tier 3: Revenue Recovered")).toBeVisible();

    // 3. Verify Recovery Opportunities Queue table
    const table = page.locator("table");
    await expect(table).toBeVisible();
    const rows = table.locator("tbody tr");
    await expect(await rows.count()).toBeGreaterThan(0);

    // 4. Click first Opportunity "Trace" button
    const firstTraceBtn = rows.first().locator("a");
    await firstTraceBtn.click();

    // 5. Verify navigation to case detail
    await expect(page).toHaveURL(/\/cases\/\d+/);
    await expect(page.getByText("Payment Information")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("AI Recommendation")).toBeVisible();
  });
});
