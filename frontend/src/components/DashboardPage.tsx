import { useEffect, useMemo, useState } from "react";

import {
  bootstrapDemoWorkspace,
  getSystemStatus,
  type SystemStatus,
} from "../lib/api";
import { connectWorkspaceSocket } from "../lib/ws";

export function DashboardPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState("");
  const [wsState, setWsState] = useState("disconnected");
  const [workspaceId, setWorkspaceId] = useState<number>(1);
  const wsEnabled = useMemo(() => workspaceId > 0, [workspaceId]);

  useEffect(() => {
    let mounted = true;
    getSystemStatus()
      .then((data) => {
        if (mounted) setStatus(data);
      })
      .catch((e: unknown) => {
        if (mounted) setError(String(e));
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!wsEnabled) return;

    const conn = connectWorkspaceSocket(
      workspaceId,
      () => setWsState("connected"),
      () => setWsState("disconnected"),
      (message) => {
        setWsState("error");
        setError(message);
      },
    );

    return () => conn.close();
  }, [workspaceId, wsEnabled]);

  const handleBootstrap = async () => {
    setError("");
    try {
      const boot = await bootstrapDemoWorkspace();
      setWorkspaceId(boot.workspace_id);
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  return (
    <section className="stack">
      <h2>Realtime Dashboard</h2>
      <div className="card-grid">
        <article className="card">
          <h3>System Status</h3>
          {status ? (
            <ul>
              <li>API: {status.status}</li>
              <li>DB connected: {String(status.db_connected)}</li>
              <li>Provider: {status.provider}</li>
              <li>Environment: {status.environment}</li>
            </ul>
          ) : (
            <p>Loading status...</p>
          )}
        </article>

        <article className="card">
          <h3>Workspace Bootstrap</h3>
          <p>
            Current workspace id: <strong>{workspaceId}</strong>
          </p>
          <button onClick={handleBootstrap} className="btn-primary" type="button">
            Create Demo Workspace
          </button>
        </article>

        <article className="card">
          <h3>Realtime Socket</h3>
          <p>Connection: {wsState}</p>
          <p className="muted">
            WebSocket endpoint placeholder: /ws/workspaces/{workspaceId}
          </p>
        </article>
      </div>
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
