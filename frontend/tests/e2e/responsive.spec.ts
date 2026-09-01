import { test, expect } from "@playwright/test";

test.describe("Responsive Layout", () => {
  const viewports = [
    { name: "Desktop", width: 1440, height: 900 },
    { name: "Tablet", width: 1024, height: 768 },
    { name: "Mobile", width: 390, height: 844 },
  ];

  for (const vp of viewports) {
    test(`Renders Dashboard cleanly on ${vp.name} (${vp.width}x${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await page.waitForLoadState("networkidle");

      // Verify header and primary dashboard elements render
      await expect(page.getByText("Autonomous Revenue Recovery")).toBeVisible();
      await expect(page.getByText("Gross Revenue at Risk")).toBeVisible();
      await expect(page.getByText("Revenue Recovered").first()).toBeVisible();
    });
  }
});
