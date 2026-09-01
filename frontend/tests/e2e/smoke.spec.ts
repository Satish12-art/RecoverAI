import { test, expect } from "@playwright/test";

test.describe("Global Smoke Test", () => {
  test("Loads homepage without unhandled console errors and displays primary UI shell", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 1. App Shell Elements
    await expect(page.locator("aside")).toBeVisible();
    await expect(page.locator("aside").getByText("RecoverAI", { exact: false })).toBeVisible();
    await expect(page.getByText("Agent Online", { exact: false })).toBeVisible();

    // 2. Simulation Notice Banner
    await expect(page.getByText("SIMULATION", { exact: false }).first()).toBeVisible();

    // 3. Executive KPI Cards
    await expect(page.getByText("Gross Revenue at Risk")).toBeVisible();
    await expect(page.getByText("Potentially Recoverable").first()).toBeVisible();
    await expect(page.getByText("Expected Recovery (ERV)")).toBeVisible();
    await expect(page.getByText("Revenue Recovered").first()).toBeVisible();

    // 4. Zero unexpected console errors
    const fatalErrors = consoleErrors.filter((e) => !e.includes("favicon") && !e.includes("hydration"));
    expect(fatalErrors.length).toBe(0);
  });
});
