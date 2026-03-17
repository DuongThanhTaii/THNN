import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DevicesPage } from "../DevicesPage";
import { useAppStore } from "../../shared/state/appStore";

describe("DevicesPage", () => {
  beforeEach(() => {
    useAppStore.setState({
      workspaceId: 1,
      wsState: "disconnected",
      globalError: "",
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("registers a device and records onboarding audit", async () => {
    const user = userEvent.setup();
    render(<DevicesPage />);

    await user.click(
      screen.getAllByRole("button", { name: "Register ESP32 Device" })[0],
    );

    expect(screen.getByText("Registered Devices (1)")).toBeInTheDocument();
    expect(
      screen.getByText("Onboarded device via ESP32 registration form"),
    ).toBeInTheDocument();
  });

  it("sends template command and updates timeline", async () => {
    const user = userEvent.setup();
    render(<DevicesPage />);

    await user.click(
      screen.getAllByRole("button", { name: "Register ESP32 Device" })[0],
    );
    await user.click(screen.getByRole("button", { name: "Ping Device" }));

    expect(
      screen.getByText("Template command dispatched: PING"),
    ).toBeInTheDocument();
  });
});
