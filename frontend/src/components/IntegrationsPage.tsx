import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  getGoogleConnectInfo,
  getJiraConnectInfo,
  listIntegrationAccounts,
  simulateGoogleCallback,
  simulateJiraCallback,
} from "../lib/api";
import { useAppStore } from "../shared/state/appStore";

type ProviderKey = "jira" | "google_calendar";

type ProviderProfile = {
  runtime: "local" | "cloud";
  endpoint: string;
  model: string;
};

function providerLabel(provider: ProviderKey): string {
  return provider === "jira" ? "Jira" : "Google Calendar";
}

function providerConnectLabel(provider: ProviderKey): string {
  return provider === "jira"
    ? "Load Jira Connect Info"
    : "Load Google Connect Info";
}

function providerCallbackLabel(provider: ProviderKey): string {
  return provider === "jira"
    ? "Simulate Jira Callback"
    : "Simulate Google Callback";
}

export function IntegrationsPage() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const setWorkspaceId = useAppStore((state) => state.setWorkspaceId);
  const setGlobalError = useAppStore((state) => state.setGlobalError);

  const [activeProvider, setActiveProvider] = useState<ProviderKey>("jira");
  const [providerProfiles, setProviderProfiles] = useState<
    Record<ProviderKey, ProviderProfile>
  >({
    jira: {
      runtime: "cloud",
      endpoint: "https://jira.atlassian.com",
      model: "jira-cloud-default",
    },
    google_calendar: {
      runtime: "cloud",
      endpoint: "https://www.googleapis.com/calendar/v3",
      model: "gcal-cloud-default",
    },
  });
  const [healthCheckAt, setHealthCheckAt] = useState<string>("");
  const [callbackCode, setCallbackCode] = useState("demo_code_001");
  const [jiraInfo, setJiraInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const [googleInfo, setGoogleInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const accountsQuery = useQuery({
    queryKey: ["integration-accounts", workspaceId],
    queryFn: () => listIntegrationAccounts(workspaceId),
  });

  const jiraMutation = useMutation({
    mutationFn: () => getJiraConnectInfo(workspaceId),
    onSuccess: (data) => {
      setJiraInfo(data);
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const googleMutation = useMutation({
    mutationFn: () => getGoogleConnectInfo(workspaceId),
    onSuccess: (data) => {
      setGoogleInfo(data);
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const callbackJiraMutation = useMutation({
    mutationFn: () =>
      simulateJiraCallback({
        workspaceId,
        code: callbackCode,
        state: "dev-ui-jira",
      }),
    onSuccess: async () => {
      await accountsQuery.refetch();
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const callbackGoogleMutation = useMutation({
    mutationFn: () =>
      simulateGoogleCallback({
        workspaceId,
        code: callbackCode,
        state: "dev-ui-google",
      }),
    onSuccess: async () => {
      await accountsQuery.refetch();
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const providerState = useMemo(() => {
    const items = accountsQuery.data?.items ?? [];
    const jiraConnected = items.some((item) =>
      item.provider.toLowerCase().includes("jira"),
    );
    const googleConnected = items.some((item) =>
      item.provider.toLowerCase().includes("google"),
    );

    return {
      jiraConnected,
      googleConnected,
      jiraInfoLoaded: Boolean(jiraInfo),
      googleInfoLoaded: Boolean(googleInfo),
    };
  }, [accountsQuery.data?.items, googleInfo, jiraInfo]);

  const connectMutation =
    activeProvider === "jira" ? jiraMutation : googleMutation;
  const callbackMutation =
    activeProvider === "jira" ? callbackJiraMutation : callbackGoogleMutation;
  const activeInfo = activeProvider === "jira" ? jiraInfo : googleInfo;
  const activeConnected =
    activeProvider === "jira"
      ? providerState.jiraConnected
      : providerState.googleConnected;
  const activeProfile = providerProfiles[activeProvider];

  const activeAccount = (accountsQuery.data?.items ?? []).find((item) => {
    const provider = item.provider.toLowerCase();
    if (activeProvider === "jira") return provider.includes("jira");
    return provider.includes("google");
  });

  const healthRows = [
    {
      label: "OAuth account linked",
      ok: activeConnected,
      detail: activeConnected
        ? "Connected account found"
        : "No account linked yet",
    },
    {
      label: "Connect payload",
      ok: Boolean(activeInfo),
      detail: activeInfo ? "Payload loaded" : "Connect payload not loaded",
    },
    {
      label: "Token freshness",
      ok: Boolean(activeAccount?.token_expires_at),
      detail: activeAccount?.token_expires_at
        ? `Expires at ${activeAccount.token_expires_at}`
        : "Unknown token expiry",
    },
    {
      label: "Webhook route",
      ok: activeConnected,
      detail: activeConnected
        ? "Webhook can be validated against active provider account"
        : "Connect provider before webhook verification",
    },
  ];

  const updateProfile = <K extends keyof ProviderProfile>(
    key: K,
    value: ProviderProfile[K],
  ) => {
    setProviderProfiles((prev) => ({
      ...prev,
      [activeProvider]: {
        ...prev[activeProvider],
        [key]: value,
      },
    }));
  };

  return (
    <section className="stack">
      <h2>Integrations Wizard</h2>

      <article className="card stack compact">
        <h3>Provider Switcher</h3>
        <div className="provider-switcher">
          <button
            className={`btn-secondary ${activeProvider === "jira" ? "is-selected" : ""}`}
            type="button"
            onClick={() => setActiveProvider("jira")}
          >
            Jira
          </button>
          <button
            className={`btn-secondary ${activeProvider === "google_calendar" ? "is-selected" : ""}`}
            type="button"
            onClick={() => setActiveProvider("google_calendar")}
          >
            Google Calendar
          </button>
        </div>
        <p className="muted">
          Active wizard: <strong>{providerLabel(activeProvider)}</strong>
        </p>
      </article>

      <article className="card stack compact">
        <label>
          Workspace ID
          <input
            type="number"
            min={1}
            value={workspaceId}
            onChange={(e) => setWorkspaceId(Number(e.target.value || 1))}
          />
        </label>
        <label>
          OAuth Callback Code (dev simulate)
          <input
            type="text"
            value={callbackCode}
            onChange={(e) => setCallbackCode(e.target.value)}
            placeholder="authorization code"
          />
        </label>
      </article>

      <div className="card-grid">
        <article className="card stack">
          <h3>Provider Profile Manager</h3>
          <p className="muted">
            Configure runtime profile for {providerLabel(activeProvider)}.
          </p>
          <label className="stack compact">
            Runtime
            <select
              value={activeProfile.runtime}
              onChange={(event) =>
                updateProfile(
                  "runtime",
                  event.target.value as "local" | "cloud",
                )
              }
            >
              <option value="local">local</option>
              <option value="cloud">cloud</option>
            </select>
          </label>
          <label className="stack compact">
            Endpoint
            <input
              value={activeProfile.endpoint}
              onChange={(event) =>
                updateProfile("endpoint", event.target.value)
              }
            />
          </label>
          <label className="stack compact">
            Profile
            <input
              value={activeProfile.model}
              onChange={(event) => updateProfile("model", event.target.value)}
            />
          </label>
          <pre>{JSON.stringify(activeProfile, null, 2)}</pre>
        </article>

        <article className="card stack">
          <h3>Provider Health & Webhooks</h3>
          <button
            className="btn-secondary"
            type="button"
            onClick={() => setHealthCheckAt(new Date().toLocaleString())}
          >
            Run Health Check
          </button>
          {healthCheckAt ? (
            <p className="muted">Last check: {healthCheckAt}</p>
          ) : null}
          <ul className="health-list">
            {healthRows.map((row) => (
              <li key={row.label}>
                <span className={`status-dot ${row.ok ? "ok" : "off"}`} />
                <div className="stack compact">
                  <strong>{row.label}</strong>
                  <span className="muted">{row.detail}</span>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <div className="card-grid">
        <article className="card stack integration-wizard">
          <h3>{providerLabel(activeProvider)} Connection Wizard</h3>
          <ol className="wizard-steps">
            <li className={activeInfo ? "done" : "pending"}>
              Step 1: Load provider connect payload
            </li>
            <li className={activeConnected ? "done" : "pending"}>
              Step 2: Simulate callback and establish account link
            </li>
            <li className={activeConnected ? "done" : "pending"}>
              Step 3: Verify connection in status panel
            </li>
          </ol>
          <div className="toolbar">
            <button
              className="btn-primary"
              type="button"
              onClick={() => void connectMutation.mutateAsync()}
              disabled={connectMutation.isPending}
            >
              {connectMutation.isPending
                ? "Loading..."
                : providerConnectLabel(activeProvider)}
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => void callbackMutation.mutateAsync()}
              disabled={callbackMutation.isPending}
            >
              {callbackMutation.isPending
                ? "Processing..."
                : providerCallbackLabel(activeProvider)}
            </button>
          </div>
          {activeInfo ? <pre>{JSON.stringify(activeInfo, null, 2)}</pre> : null}
        </article>

        <article className="card stack integration-status">
          <h3>Connection Status Panel</h3>
          <div className="status-grid">
            <div className="status-item">
              <span
                className={`status-dot ${providerState.jiraConnected ? "ok" : "off"}`}
              />
              <strong>Jira</strong>
              <span className="muted">
                {providerState.jiraConnected ? "Connected" : "Not connected"}
              </span>
            </div>
            <div className="status-item">
              <span
                className={`status-dot ${providerState.googleConnected ? "ok" : "off"}`}
              />
              <strong>Google Calendar</strong>
              <span className="muted">
                {providerState.googleConnected ? "Connected" : "Not connected"}
              </span>
            </div>
          </div>
          <button
            className="btn-secondary"
            type="button"
            onClick={() => void accountsQuery.refetch()}
          >
            Refresh Accounts
          </button>
        </article>
      </div>

      <article className="card stack">
        <h3>Connected Accounts ({accountsQuery.data?.count ?? 0})</h3>
        {!accountsQuery.data || accountsQuery.data.items.length === 0 ? (
          <p className="muted">No accounts connected for this workspace.</p>
        ) : (
          <ul className="list">
            {accountsQuery.data.items.map((account) => (
              <li key={account.id}>
                <div className="stack compact">
                  <strong>{account.provider}</strong>
                  <span>{account.account_label || "(no label)"}</span>
                  <span className="muted">
                    Expires: {account.token_expires_at || "unknown"}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
