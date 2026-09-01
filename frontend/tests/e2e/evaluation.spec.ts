import { test, expect } from "@playwright/test";

test.describe("Evaluation & Benchmark Page", () => {
  test("Renders comparison table, correct terminology, confusion matrix, calibration, and safety scorecard", async ({ page }) => {
    await page.goto("/evaluation");
    await page.waitForLoadState("networkidle");

    // 1. Comparison table & Macro F1 uplift
    await expect(page.getByText("RecoverAI vs. Naive Retry Baseline")).toBeVisible();
    await expect(page.getByText("+24.20 pp Macro F1").first()).toBeVisible();
    await expect(page.getByText("Action Classification Macro F1")).toBeVisible();
    await expect(page.getByText("Zero-Regret Decision Rate").first()).toBeVisible();

    // 2. Strict Terminology check: "Ground Truth Label Revenue" must appear, NOT "Maximum Theoretical Revenue"
    await expect(page.getByText("GROUND TRUTH LABEL REVENUE").first()).toBeVisible();
    const pageContent = await page.content();
    expect(pageContent).not.toContain("Maximum Theoretical Revenue");

    // 3. 4x4 Confusion Matrix
    await expect(page.getByText("4×4 Action Confusion Matrix")).toBeVisible();

    // 4. Statistical Calibration (Brier score & ECE)
    await expect(page.getByText("Statistical Calibration")).toBeVisible();
    await expect(page.getByText("Brier Score").first()).toBeVisible();
    await expect(page.getByText("Expected Calibration Error").first()).toBeVisible();

    // 5. Safety & Governance Scorecard (100% Passed)
    await expect(page.getByText("Safety & Governance Scorecard")).toBeVisible();
    await expect(page.getByText("100% PASSED").first()).toBeVisible();
    await expect(page.getByText("Policy Violations").first()).toBeVisible();

    // 6. Runtime Efficiency
    await expect(page.getByText("Agent Runtime Efficiency")).toBeVisible();
  });
});
