import { test, expect } from "@playwright/test";

test.describe("Master 3-Minute Hackathon Judge Demo Flow", () => {
  test("Executes full canonical demo workflow end-to-end", async ({ page }) => {
    // 1. Open Dashboard & Observe Revenue KPIs
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Gross Revenue at Risk")).toBeVisible();
    await expect(page.getByText("Potentially Recoverable").first()).toBeVisible();

    // 2. Open First High-Value Recovery Opportunity
    const rows = page.locator("table tbody tr");
    await expect(await rows.count()).toBeGreaterThan(0);
    await rows.first().locator("a").click();

    // 3. Inspect Case Detail, Context, and State Machine Trace
    await expect(page).toHaveURL(/\/cases\/\d+/);
    await expect(page.getByText("Payment Information")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Customer Profile & History")).toBeVisible();
    await expect(page.getByText("AI Recommendation")).toBeVisible();
    await expect(page.getByText("Policy Engine Decision")).toBeVisible();
    await expect(page.getByText("Bounded State Machine Timeline")).toBeVisible();

    // 4. Return to Dashboard & Run 10-Case Simulation
    await page.click('aside a[href="/"]');
    await expect(page).toHaveURL(/\/$/);
    await page.click('button:has-text("10")');
    await page.getByRole("button", { name: /Run Recovery Simulation/i }).click();
    await expect(page.getByText("Batch Complete", { exact: false })).toBeVisible({ timeout: 15000 });

    // 5. Open Evaluation & Inspect Benchmark Metrics
    await page.click('aside a[href="/evaluation"]');
    await expect(page).toHaveURL(/\/evaluation/);
    await expect(page.getByText("+24.20 pp Macro F1").first()).toBeVisible();
    await expect(page.getByText("GROUND TRUTH LABEL REVENUE").first()).toBeVisible();
    await expect(page.getByText("4×4 Action Confusion Matrix")).toBeVisible();
    await expect(page.getByText("100% PASSED").first()).toBeVisible();

    // 6. Open Audit Trail & Verify Governance Guardrails
    await page.click('aside a[href="/audit"]');
    await expect(page).toHaveURL(/\/audit/);
    await expect(page.getByText("Active Deterministic Policy Guardrails (10 Rules)")).toBeVisible();

    // 7. Return to Dashboard & Trigger Razorpay Test Webhook Ingestion
    await page.click('aside a[href="/"]');
    const sendBtn = page.getByRole("button", { name: /Send Test Razorpay Webhook/i });
    await sendBtn.click();
    await expect(page.getByText("Webhook Ingested & Evaluated", { exact: false })).toBeVisible({ timeout: 10000 });
  });
});
