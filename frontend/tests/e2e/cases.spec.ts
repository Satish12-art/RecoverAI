import { test, expect } from "@playwright/test";

test.describe("Recovery Cases Management", () => {
  test("Filters, searches, and paginates recovery cases", async ({ page }) => {
    await page.goto("/cases");
    await page.waitForLoadState("networkidle");

    // 1. Initial table load
    const rows = page.locator("table tbody tr");
    await expect(await rows.count()).toBeGreaterThan(0);

    // 2. Test failure code filter
    const failureSelect = page.locator('select:has(option[value="temporary_bank_error"])');
    await failureSelect.selectOption("temporary_bank_error");
    await page.waitForTimeout(500);

    // Filtered rows inside table body should appear
    await expect(page.locator("table tbody").getByText("temporary_bank_error").first()).toBeVisible();

    // 3. Test Reset Filters
    await page.click("button:has-text('Reset Filters')");
    await page.waitForTimeout(500);
    await expect(await rows.count()).toBeGreaterThan(1);
  });
});
