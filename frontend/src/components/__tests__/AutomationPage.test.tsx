import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AutomationPage } from "../AutomationPage";
import { useAppStore } from "../../shared/state/appStore";
import { useAuthStore } from "../../shared/state/authStore";

const listAutomationsMock = vi.fn();
const createAutomationMock = vi.fn();
const getSyncStatusMock = vi.fn();

vi.mock("../../lib/api", async () => {
  const actual =
    await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    listAutomations: (...args: unknown[]) => listAutomationsMock(...args),
    createAutomation: (...args: unknown[]) => createAutomationMock(...args),
    getSyncStatus: (...args: unknown[]) => getSyncStatusMock(...args),
  };
});

describe("AutomationPage", () => {
  beforeEach(() => {
    useAppStore.setState({
      workspaceId: 1,
      wsState: "disconnected",
      globalError: "",
    });
    useAuthStore.setState({
      accessToken: "token-a",
      refreshToken: "token-b",
      expiresAt: new Date(Date.now() + 30 * 60_000).toISOString(),
      userEmail: "owner@agent.local",
      role: "owner",
      isAuthenticated: true,
    });

    listAutomationsMock.mockResolvedValue([]);
    createAutomationMock.mockResolvedValue({
      id: "rule-1",
      workspace_id: 1,
      name: "Daily Jira to Calendar Sync",
      trigger_type: "schedule",
      action_type: "sync_bidirectional",
      config: {
        schedule: "0 8 * * *",
        source: "jira",
        target: "google_calendar",
      },
      enabled: true,
    });
    getSyncStatusMock.mockResolvedValue({
      workspace_id: 1,
      healthy: true,
      inflight: 0,
      retry_queue: 0,
      dead_letter_count: 0,
      last_event_at: null,
      conflicts: [],
    });
  });

  it("creates a new automation rule", async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AutomationPage />
      </QueryClientProvider>,
    );

    const ruleNameInput = screen.getByLabelText("Rule name");
    await user.clear(ruleNameInput);
    await user.type(ruleNameInput, "Morning Sync");

    await user.click(
      screen.getByRole("button", { name: "Save Automation Rule" }),
    );

    await waitFor(() => {
      expect(createAutomationMock).toHaveBeenCalledTimes(1);
    });
    expect(createAutomationMock.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        workspace_id: 1,
        name: "Morning Sync",
      }),
    );
  });
});
