import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("login page has no critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).analyze();

  const critical = results.violations.filter((v) =>
    ["critical", "serious"].includes(v.impact || ""),
  );

  expect(critical).toEqual([]);
});

test("dashboard shell has no critical accessibility violations", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "token-a",
        refresh_token: "token-b",
        expires_at: new Date(Date.now() + 30 * 60_000).toISOString(),
        email: "owner@agent.local",
        role: "owner",
      }),
    });
  });

  await page.route("**/api/v1/workspaces**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: 1, slug: "main", name: "Main Workspace", owner_user_id: 1 },
      ]),
    });
  });

  await page.route("**/api/v1/system/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        db_connected: true,
        provider: "demo",
        environment: "test",
      }),
    });
  });

  await page.route("**/api/v1/tasks**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/v1/integrations/accounts**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ workspace_id: 1, count: 0, items: [] }),
    });
  });

  await page.route("**/api/v1/sync/status**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        workspace_id: 1,
        health: "healthy",
        policies_total: 1,
        policies_enabled: 1,
        conflicts_open: 0,
        conflicts_resolved: 0,
        last_conflict_at: null,
        recent_conflicts: [],
      }),
    });
  });

  await page.route("**/api/v1/automations**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(
    page.getByRole("heading", { name: "Realtime Dashboard" }),
  ).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const critical = results.violations.filter((v) =>
    ["critical", "serious"].includes(v.impact || ""),
  );

  expect(critical).toEqual([]);
});
