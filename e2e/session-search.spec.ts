import { test, expect } from "@playwright/test";

test("searches sessions and shows resume command", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Search sessions")).toBeVisible();
  await page.getByLabel("Search sessions").fill("orchid");
  await expect(page.getByText("claude --resume")).toBeVisible();
});
