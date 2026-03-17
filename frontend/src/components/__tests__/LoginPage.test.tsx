import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "../LoginPage";
import { useAuthStore } from "../../shared/state/authStore";
import { useAppStore } from "../../shared/state/appStore";

const loginAuthMock = vi.fn();

vi.mock("../../lib/api", async () => {
  const actual =
    await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    loginAuth: (...args: unknown[]) => loginAuthMock(...args),
  };
});

describe("LoginPage", () => {
  beforeEach(() => {
    loginAuthMock.mockReset();
    useAppStore.setState({
      workspaceId: 1,
      wsState: "disconnected",
      globalError: "",
    });
    useAuthStore.setState({
      accessToken: "",
      refreshToken: "",
      expiresAt: "",
      userEmail: "",
      role: "viewer",
      isAuthenticated: false,
    });
  });

  it("signs in successfully and updates auth state", async () => {
    loginAuthMock.mockResolvedValue({
      accessToken: "a",
      refreshToken: "b",
      expiresAt: new Date(Date.now() + 15 * 60_000).toISOString(),
      userEmail: "owner@agent.local",
      role: "owner",
    });

    const queryClient = new QueryClient();
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Signed in successfully."),
    ).toBeInTheDocument();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });
});
