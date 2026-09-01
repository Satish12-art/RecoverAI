import { test, expect } from "@playwright/test";

test.describe("Security & Ground Truth Isolation E2E", () => {
  test("Ensures raw ground truth file is inaccessible and zero credentials/secrets are exposed", async ({ page }) => {
    // 1. Check raw ground truth is NOT served as a static public file
    const response = await page.goto("/ground_truth.json", { waitUntil: "commit" });
    // Should be 404 or routed to Next.js not-found
    expect(response?.status()).toBe(404);

    // 2. Open dashboard and check page content for zero leaked API keys
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    const content = await page.content();

    expect(content).not.toContain("razorpay_key_secret");
    expect(content).not.toContain("webhook_secret_here");
    expect(content).not.toContain("gemini_api_key");
  });
});
