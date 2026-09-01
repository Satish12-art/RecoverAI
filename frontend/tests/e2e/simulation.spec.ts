import { test, expect } from "@playwright/test";

test.describe("Live Simulation Runner", () => {
  test("Executes batch simulation and renders completed results", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 1. Select 10 batch size
    await page.click('button:has-text("10")');

    // 2. Click Run Recovery Simulation
    const runBtn = page.getByRole("button", { name: /Run Recovery Simulation/i });
    await runBtn.click();

    // 3. Verify loading state
    await expect(page.getByText("Running Recovery Agent...")).toBeVisible();

    // 4. Verify batch complete summary appears
    await expect(page.getByText("Batch Complete", { exact: false })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Recovered This Batch:", { exact: false })).toBeVisible();
  });
});
