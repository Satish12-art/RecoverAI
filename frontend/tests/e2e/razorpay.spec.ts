import { test, expect } from "@playwright/test";

test.describe("Razorpay Test-Mode Webhook Ingestion E2E", () => {
  test("Triggers a test webhook from dashboard console and creates actionable recovery case", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 1. Verify Razorpay test console card is present
    await expect(page.getByText("Razorpay Test-Mode Webhook Ingestion")).toBeVisible();
    await expect(page.getByText("TEST MODE ONLY")).toBeVisible();

    // 2. Click Send Test Razorpay Webhook
    const sendBtn = page.getByRole("button", { name: /Send Test Razorpay Webhook/i });
    await sendBtn.click();

    // 3. Verify real-time confirmation appears
    await expect(page.getByText("Webhook Ingested & Evaluated", { exact: false })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("pay_test_", { exact: false }).first()).toBeVisible();
  });
});
