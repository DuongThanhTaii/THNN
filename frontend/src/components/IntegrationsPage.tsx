import { useState } from "react";

import { getGoogleConnectInfo, getJiraConnectInfo } from "../lib/api";

export function IntegrationsPage() {
  const [jiraInfo, setJiraInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const [googleInfo, setGoogleInfo] = useState<Record<string, unknown> | null>(
    null,
  );
  const [error, setError] = useState("");

  const fetchJira = async () => {
    setError("");
    try {
      const info = await getJiraConnectInfo();
      setJiraInfo(info);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const fetchGoogle = async () => {
    setError("");
    try {
      const info = await getGoogleConnectInfo();
      setGoogleInfo(info);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  return (
    <section className="stack">
      <h2>Integrations</h2>

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

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
