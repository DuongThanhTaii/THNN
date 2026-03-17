import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IntegrationsPage } from "../IntegrationsPage";
import { useAppStore } from "../../shared/state/appStore";

const listIntegrationAccountsMock = vi.fn();
const getJiraConnectInfoMock = vi.fn();
const getGoogleConnectInfoMock = vi.fn();
const simulateJiraCallbackMock = vi.fn();
const simulateGoogleCallbackMock = vi.fn();

vi.mock("../../lib/api", async () => {
  const actual =
    await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    listIntegrationAccounts: (...args: unknown[]) =>
      listIntegrationAccountsMock(...args),
    getJiraConnectInfo: (...args: unknown[]) => getJiraConnectInfoMock(...args),
    getGoogleConnectInfo: (...args: unknown[]) =>
      getGoogleConnectInfoMock(...args),
    simulateJiraCallback: (...args: unknown[]) =>
      simulateJiraCallbackMock(...args),
    simulateGoogleCallback: (...args: unknown[]) =>
      simulateGoogleCallbackMock(...args),
  };
});

describe("IntegrationsPage", () => {
  beforeEach(() => {
    useAppStore.setState({
      workspaceId: 1,
      wsState: "disconnected",
      globalError: "",
    });

    listIntegrationAccountsMock.mockResolvedValue({
      workspace_id: 1,
      count: 0,
      items: [],
    });
    getJiraConnectInfoMock.mockResolvedValue({ url: "jira-connect" });
    getGoogleConnectInfoMock.mockResolvedValue({ url: "google-connect" });
    simulateJiraCallbackMock.mockResolvedValue({ ok: true });
    simulateGoogleCallbackMock.mockResolvedValue({ ok: true });
  });

  it("switches provider wizard and loads connect info", async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <IntegrationsPage />
      </QueryClientProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Google Calendar" }));
    expect(screen.getByText("Active wizard:")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Load Google Connect Info" }),
    );
    expect(getGoogleConnectInfoMock).toHaveBeenCalled();
  });
});
