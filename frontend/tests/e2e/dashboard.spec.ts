import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  let accounts = { workspace_id: 1, count: 0, items: [] as unknown[] };

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
      body: JSON.stringify(accounts),
    });
  });

  await page.route("**/api/v1/integrations/jira/connect**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        url: "https://jira.local/oauth",
        state: "jira-state",
      }),
    });
  });

  await page.route(
    "**/api/v1/integrations/google_calendar/connect**",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          url: "https://google.local/oauth",
          state: "google-state",
        }),
      });
    },
  );

  await page.route("**/api/v1/integrations/jira/callback**", async (route) => {
    accounts = {
      workspace_id: 1,
      count: 1,
      items: [
        {
          id: 1,
          provider: "jira",
          account_label: "jira-owner",
          token_expires_at: new Date(Date.now() + 86_400_000).toISOString(),
        },
      ],
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route(
    "**/api/v1/integrations/google_calendar/callback**",
    async (route) => {
      accounts = {
        workspace_id: 1,
        count: 2,
        items: [
          {
            id: 1,
            provider: "jira",
            account_label: "jira-owner",
            token_expires_at: new Date(Date.now() + 86_400_000).toISOString(),
          },
          {
            id: 2,
            provider: "google_calendar",
            account_label: "google-owner",
            token_expires_at: new Date(Date.now() + 86_400_000).toISOString(),
          },
        ],
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true }),
      });
    },
  );

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
    const method = route.request().method();
    if (method === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 10,
          workspace_id: 1,
          name: "auto",
          trigger_type: "schedule",
          action_type: "sync_bidirectional",
          config: {},
          enabled: true,
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
});

test("login and navigate core dashboard journeys", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(
    page.getByRole("heading", { name: "Realtime Dashboard" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Tasks" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();

  await page.getByRole("link", { name: "Devices" }).click();
  await expect(
    page.getByRole("heading", { name: "ESP32 Device Control" }),
  ).toBeVisible();
});

test("configure integrations and automation from app shell", async ({
  page,
}) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(
    page.getByRole("heading", { name: "Realtime Dashboard" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Integrations" }).click();
  await expect(
    page.getByRole("heading", { name: "Integrations Wizard" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Load Jira Connect Info" }).click();
  await page.getByRole("button", { name: "Simulate Jira callback" }).click();
  await expect(page.getByText("jira-owner")).toBeVisible();

  await page.getByRole("link", { name: "Automation" }).click();
  await expect(
    page.getByRole("heading", { name: "Automation & Sync Control" }),
  ).toBeVisible();
  await page.getByLabel("Rule name").fill("Morning sync");
  await page.getByRole("button", { name: "Save Automation Rule" }).click();
});
