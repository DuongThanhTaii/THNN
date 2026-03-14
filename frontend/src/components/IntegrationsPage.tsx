import { useState } from "react";

import {
  getGoogleConnectInfo,
  getJiraConnectInfo,
  listIntegrationAccounts,
  simulateGoogleCallback,
  simulateJiraCallback,
  type IntegrationAccount,
} from "../lib/api";

export function IntegrationsPage() {
  const [workspaceId, setWorkspaceId] = useState(1);
  const [callbackCode, setCallbackCode] = useState("demo_code_001");
  const [jiraInfo, setJiraInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const [googleInfo, setGoogleInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const [accounts, setAccounts] = useState<IntegrationAccount[]>([]);
  const [accountsCount, setAccountsCount] = useState(0);
  const [error, setError] = useState("");

  const fetchJira = async () => {
    setError("");
    try {
      const info = await getJiraConnectInfo(workspaceId);
      setJiraInfo(info);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const fetchGoogle = async () => {
    setError("");
    try {
      const info = await getGoogleConnectInfo(workspaceId);
      setGoogleInfo(info);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const fetchAccounts = async () => {
    setError("");
    try {
      const data = await listIntegrationAccounts(workspaceId);
      setAccounts(data.items);
      setAccountsCount(data.count);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const callbackJira = async () => {
    setError("");
    try {
      await simulateJiraCallback({
        workspaceId,
        code: callbackCode,
        state: "dev-ui-jira",
      });
      await fetchAccounts();
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const callbackGoogle = async () => {
    setError("");
    try {
      await simulateGoogleCallback({
        workspaceId,
        code: callbackCode,
        state: "dev-ui-google",
      });
      await fetchAccounts();
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  return (
    <section className="stack">
      <h2>Integrations</h2>

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
        <div className="toolbar">
          <button className="btn-secondary" type="button" onClick={fetchAccounts}>
            Refresh Accounts
          </button>
          <button className="btn-secondary" type="button" onClick={callbackJira}>
            Simulate Jira Callback
          </button>
          <button className="btn-secondary" type="button" onClick={callbackGoogle}>
            Simulate Google Callback
          </button>
        </div>
      </article>

      <div className="card-grid">
        <article className="card stack">
          <h3>Jira</h3>
          <button className="btn-primary" type="button" onClick={fetchJira}>
            Load Jira Connect Info
          </button>
          {jiraInfo ? <pre>{JSON.stringify(jiraInfo, null, 2)}</pre> : null}
        </article>

        <article className="card stack">
          <h3>Google Calendar</h3>
          <button className="btn-primary" type="button" onClick={fetchGoogle}>
            Load Google Connect Info
          </button>
          {googleInfo ? <pre>{JSON.stringify(googleInfo, null, 2)}</pre> : null}
        </article>
      </div>

      <article className="card stack">
        <h3>Connected Accounts ({accountsCount})</h3>
        {accounts.length === 0 ? (
          <p className="muted">No accounts connected for this workspace.</p>
        ) : (
          <ul className="list">
            {accounts.map((account) => (
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

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
