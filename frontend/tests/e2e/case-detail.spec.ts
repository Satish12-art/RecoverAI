import { test, expect } from "@playwright/test";

test.describe("Case Detail & Agent Trace Inspector", () => {
  test("Displays complete structured context, policy checklist, and state machine timeline", async ({ page }) => {
    page.on("pageerror", (err) => console.log("PAGE ERROR:", err.message));
    page.on("console", (msg) => {
      if (msg.type() === "error") console.log("CONSOLE ERROR:", msg.text());
    });

    // 1. Go to Cases list and click the first Inspect button
    await page.goto("/cases");
    await page.waitForLoadState("networkidle");

    const inspectLink = page.locator("table tbody tr a").first();
    await expect(inspectLink).toBeVisible();
    await inspectLink.click();

    // 2. Payment Information Card (with timeout for API fetch)
    await expect(page.getByText("Payment Information")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Amount at Risk")).toBeVisible();

    // 3. Customer Profile & History
    await expect(page.getByText("Customer Profile & History")).toBeVisible();
    await expect(page.getByText("Payment History")).toBeVisible();

    // 4. Recovery Intelligence Scorer Card
    await expect(page.getByText("Recovery Intelligence")).toBeVisible();
    await expect(page.getByText("Probability", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Confidence", { exact: true }).first()).toBeVisible();

    // 5. AI Recommendation & Policy Engine Check Cards
    await expect(page.getByText("AI Recommendation")).toBeVisible();
    await expect(page.getByText("Policy Engine Decision")).toBeVisible();
    await expect(page.getByText("Payment not already paid")).toBeVisible();
    await expect(page.getByText("Fraud / Velocity check")).toBeVisible();

    // 6. State Machine Timeline
    await expect(page.getByText("Bounded State Machine Timeline")).toBeVisible();
    await expect(page.getByText("DETECTED")).toBeVisible();
    await expect(page.getByText("ELIGIBILITY CHECK")).toBeVisible();
    await expect(page.getByText("CONTEXT LOADING")).toBeVisible();
    await expect(page.getByText("SCORING")).toBeVisible();
    await expect(page.getByText("TERMINAL")).toBeVisible();
  });
});
