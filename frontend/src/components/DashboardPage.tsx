import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  bootstrapDemoWorkspace,
  createTask,
  getSystemStatus,
  listIntegrationAccounts,
  listTasksFiltered,
} from "../lib/api";
import { type RealtimeMessage, connectWorkspaceSocket } from "../lib/ws";
import { useAppStore } from "../shared/state/appStore";

type ActivityEntry = {
  id: string;
  label: string;
  details: string;
  occurredAt: number;
};

const MAX_FEED_ITEMS = 30;

type TimelineMarker = {
  kind: "jira" | "calendar" | "task";
  label: string;
};

type TimelineDay = {
  isoDate: string;
  dayLabel: string;
  markers: TimelineMarker[];
};

function formatMessage(message: RealtimeMessage): Omit<ActivityEntry, "id"> {
  const timestamp =
    typeof message.timestamp === "number"
      ? message.timestamp * 1000
      : Date.now();

  if (message.type === "connected") {
    return {
      label: "Channel Connected",
      details: message.message || "Realtime channel established",
      occurredAt: timestamp,
    };
  }

  if (message.type === "heartbeat") {
    return {
      label: "Heartbeat",
      details: `Workspace ${message.workspace_id ?? "-"}`,
      occurredAt: timestamp,
    };
  }

  if (message.type === "event") {
    return {
      label: `Server Event: ${message.event_type || "unknown"}`,
      details: JSON.stringify(message.payload ?? {}),
      occurredAt: timestamp,
    };
  }

  if (message.type === "client_event") {
    return {
      label: "Client Echo Event",
      details: JSON.stringify(message.payload ?? {}),
      occurredAt: timestamp,
    };
  }

  return {
    label: `Message: ${message.type}`,
    details: JSON.stringify(message.payload ?? message),
    occurredAt: timestamp,
  };
}

export function DashboardPage() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const wsState = useAppStore((state) => state.wsState);
  const setWorkspaceId = useAppStore((state) => state.setWorkspaceId);
  const setWsState = useAppStore((state) => state.setWsState);
  const setGlobalError = useAppStore((state) => state.setGlobalError);
  const [feed, setFeed] = useState<ActivityEntry[]>([]);
  const [quickActionStatus, setQuickActionStatus] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchScope, setSearchScope] = useState<
    "all" | "tasks" | "integrations"
  >("all");
  const [taskStatusFilter, setTaskStatusFilter] = useState<
    "all" | "todo" | "in_progress" | "done" | "blocked"
  >("all");

  const feedSummary = useMemo(() => {
    const eventCount = feed.filter((item) =>
      item.label.startsWith("Server Event"),
    ).length;
    const heartbeatCount = feed.filter(
      (item) => item.label === "Heartbeat",
    ).length;
    return { eventCount, heartbeatCount };
  }, [feed]);

  const statusQuery = useQuery({
    queryKey: ["system-status"],
    queryFn: getSystemStatus,
  });

  const timelineTasksQuery = useQuery({
    queryKey: ["tasks", "timeline", workspaceId],
    queryFn: () =>
      listTasksFiltered({
        workspaceId,
        limit: 50,
        offset: 0,
      }),
    enabled: workspaceId > 0,
  });

  const accountsQuery = useQuery({
    queryKey: ["integration-accounts", "timeline", workspaceId],
    queryFn: () => listIntegrationAccounts(workspaceId),
    enabled: workspaceId > 0,
  });

  const timelineDays = useMemo<TimelineDay[]>(() => {
    const now = new Date();
    const days: TimelineDay[] = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(now);
      date.setDate(now.getDate() + index);
      const isoDate = date.toISOString().slice(0, 10);
      return {
        isoDate,
        dayLabel: date.toLocaleDateString(undefined, {
          weekday: "short",
          month: "short",
          day: "numeric",
        }),
        markers: [],
      };
    });

    const byIndex = days.map((day) => ({ ...day, markers: [...day.markers] }));
    const tasks = timelineTasksQuery.data ?? [];
    tasks.forEach((task, idx) => {
      const bucket = byIndex[(task.id + idx) % byIndex.length];
      bucket.markers.push({
        kind: "task",
        label: `${task.title.slice(0, 24)}${task.title.length > 24 ? "..." : ""}`,
      });
    });

    const accounts = accountsQuery.data?.items ?? [];
    const hasJira = accounts.some((item) =>
      item.provider.toLowerCase().includes("jira"),
    );
    const hasGoogle = accounts.some((item) =>
      item.provider.toLowerCase().includes("google"),
    );

    if (hasJira) {
      byIndex[1]?.markers.push({ kind: "jira", label: "JIRA-Planning Sync" });
      byIndex[4]?.markers.push({ kind: "jira", label: "JIRA-Issue Grooming" });
    }

    if (hasGoogle) {
      byIndex[2]?.markers.push({ kind: "calendar", label: "Calendar Standup" });
      byIndex[5]?.markers.push({
        kind: "calendar",
        label: "Calendar Sprint Review",
      });
    }

    return byIndex;
  }, [accountsQuery.data, timelineTasksQuery.data]);

  const globalSearchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const tasks = timelineTasksQuery.data ?? [];
    const accounts = accountsQuery.data?.items ?? [];

    const taskItems = tasks
      .filter((task) =>
        taskStatusFilter === "all" ? true : task.status === taskStatusFilter,
      )
      .filter((task) => {
        if (!q) return true;
        const haystack =
          `${task.title} ${task.description || ""} ${task.status} ${task.priority}`.toLowerCase();
        return haystack.includes(q);
      })
      .map((task) => ({
        id: `task-${task.id}`,
        kind: "task" as const,
        title: task.title,
        subtitle: `#${task.id} ${task.status} ${task.priority}`,
      }));

    const accountItems = accounts
      .filter((account) => {
        if (!q) return true;
        const haystack =
          `${account.provider} ${account.account_label} ${account.token_expires_at || ""}`.toLowerCase();
        return haystack.includes(q);
      })
      .map((account) => ({
        id: `integration-${account.id}`,
        kind: "integration" as const,
        title: account.account_label || account.provider,
        subtitle: `${account.provider} expires ${account.token_expires_at || "unknown"}`,
      }));

    if (searchScope === "tasks") return taskItems;
    if (searchScope === "integrations") return accountItems;
    return [...taskItems, ...accountItems];
  }, [
    accountsQuery.data?.items,
    searchQuery,
    searchScope,
    taskStatusFilter,
    timelineTasksQuery.data,
  ]);

  const bootstrapMutation = useMutation({
    mutationFn: bootstrapDemoWorkspace,
    onSuccess: (data) => {
      setWorkspaceId(data.workspace_id);
      setGlobalError("");
    },
    onError: (error) => {
      setGlobalError(String(error));
    },
  });

  const quickCreateTaskMutation = useMutation({
    mutationFn: () =>
      createTask({
        workspace_id: workspaceId,
        title: `Quick action task ${new Date().toLocaleTimeString()}`,
        description: "Created from dashboard command center",
      }),
    onSuccess: (task) => {
      setQuickActionStatus(`Created task #${task.id}`);
      setGlobalError("");
      void timelineTasksQuery.refetch();
    },
    onError: (error) => {
      setQuickActionStatus("Action failed");
      setGlobalError(String(error));
    },
  });

  useEffect(() => {
    if (workspaceId <= 0) return;

    const conn = connectWorkspaceSocket(
      workspaceId,
      () => setWsState("connected"),
      () => setWsState("disconnected"),
      (message) => {
        setWsState("error");
        setGlobalError(message);
      },
      (message) => {
        const mapped = formatMessage(message);
        setFeed((prev) => {
          const next: ActivityEntry[] = [
            {
              ...mapped,
              id: `${mapped.occurredAt}-${Math.random().toString(36).slice(2, 8)}`,
            },
            ...prev,
          ];
          return next.slice(0, MAX_FEED_ITEMS);
        });
      },
    );

    return () => conn.close();
  }, [workspaceId, setGlobalError, setWsState]);

  const handleBootstrap = async () => {
    setGlobalError("");
    await bootstrapMutation.mutateAsync();
  };

  const runQuickAction = async (
    action: "status" | "timeline" | "bootstrap",
  ) => {
    setQuickActionStatus("Running...");
    try {
      if (action === "status") {
        await statusQuery.refetch();
        setQuickActionStatus("System status refreshed");
        return;
      }
      if (action === "timeline") {
        await Promise.all([
          timelineTasksQuery.refetch(),
          accountsQuery.refetch(),
        ]);
        setQuickActionStatus("Timeline data refreshed");
        return;
      }
      await bootstrapMutation.mutateAsync();
      setQuickActionStatus("Workspace bootstrap complete");
    } catch (error) {
      setQuickActionStatus("Action failed");
      setGlobalError(String(error));
    }
  };

  return (
    <section className="stack">
      <h2>Realtime Dashboard</h2>
      <div className="card-grid">
        <article className="card">
          <h3>System Status</h3>
          {statusQuery.data ? (
            <ul>
              <li>API: {statusQuery.data.status}</li>
              <li>DB connected: {String(statusQuery.data.db_connected)}</li>
              <li>Provider: {statusQuery.data.provider}</li>
              <li>Environment: {statusQuery.data.environment}</li>
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
          <button
            onClick={handleBootstrap}
            className="btn-primary"
            type="button"
            disabled={bootstrapMutation.isPending}
          >
            {bootstrapMutation.isPending
              ? "Creating..."
              : "Create Demo Workspace"}
          </button>
        </article>

        <article className="card">
          <h3>Realtime Socket</h3>
          <p>Connection: {wsState}</p>
          <p className="muted">
            WebSocket endpoint placeholder: /ws/workspaces/{workspaceId}
          </p>
        </article>

        <article className="card stack">
          <div className="toolbar">
            <h3>Activity Feed</h3>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setFeed([])}
              disabled={feed.length === 0}
            >
              Clear Feed
            </button>
          </div>
          <p className="muted">
            Total items: {feed.length}. Server events: {feedSummary.eventCount}.
            Heartbeats: {feedSummary.heartbeatCount}.
          </p>
          {feed.length === 0 ? (
            <p className="muted">Waiting for websocket activity...</p>
          ) : (
            <ul className="activity-feed">
              {feed.map((item) => (
                <li key={item.id} className="activity-item">
                  <div>
                    <strong>{item.label}</strong>
                    <p className="muted">{item.details}</p>
                  </div>
                  <time className="muted">
                    {new Date(item.occurredAt).toLocaleTimeString()}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="card stack timeline-card">
          <h3>Calendar Timeline</h3>
          <p className="muted">
            7-day view with Jira-linked markers, calendar sync milestones, and
            task placement hints.
          </p>
          <div
            className="timeline-grid"
            role="region"
            tabIndex={0}
            aria-label="Seven day calendar timeline"
          >
            {timelineDays.map((day) => (
              <section key={day.isoDate} className="timeline-day">
                <header>
                  <strong>{day.dayLabel}</strong>
                </header>
                <div className="timeline-markers">
                  {day.markers.length === 0 ? (
                    <span className="timeline-empty">No items</span>
                  ) : (
                    day.markers.map((marker, index) => (
                      <span
                        key={`${day.isoDate}-${marker.kind}-${index}`}
                        className={`timeline-marker ${marker.kind}`}
                      >
                        {marker.label}
                      </span>
                    ))
                  )}
                </div>
              </section>
            ))}
          </div>
          {timelineTasksQuery.isFetching || accountsQuery.isFetching ? (
            <p className="muted">Refreshing timeline data...</p>
          ) : null}
        </article>

        <article className="card stack">
          <h3>Command Center</h3>
          <p className="muted">
            Quick actions for common operator workflows in this workspace.
          </p>
          <div className="command-grid">
            <button
              className="btn-secondary"
              type="button"
              onClick={() => void runQuickAction("status")}
            >
              Refresh System Status
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => void runQuickAction("timeline")}
            >
              Refresh Timeline Data
            </button>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => void runQuickAction("bootstrap")}
            >
              Bootstrap Workspace
            </button>
            <button
              className="btn-primary"
              type="button"
              onClick={() => void quickCreateTaskMutation.mutateAsync()}
              disabled={quickCreateTaskMutation.isPending}
            >
              {quickCreateTaskMutation.isPending
                ? "Creating Task..."
                : "Create Quick Task"}
            </button>
          </div>
          {quickActionStatus ? (
            <p className="muted">{quickActionStatus}</p>
          ) : null}
        </article>

        <article className="card stack timeline-card">
          <h3>Global Search</h3>
          <div className="toolbar">
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search tasks, Jira/Google accounts, statuses..."
            />
            <select
              value={searchScope}
              onChange={(event) =>
                setSearchScope(
                  event.target.value as "all" | "tasks" | "integrations",
                )
              }
              aria-label="Search scope"
            >
              <option value="all">all</option>
              <option value="tasks">tasks</option>
              <option value="integrations">integrations</option>
            </select>
            <select
              value={taskStatusFilter}
              onChange={(event) =>
                setTaskStatusFilter(
                  event.target.value as
                    | "all"
                    | "todo"
                    | "in_progress"
                    | "done"
                    | "blocked",
                )
              }
              aria-label="Task status filter"
            >
              <option value="all">all status</option>
              <option value="todo">todo</option>
              <option value="in_progress">in_progress</option>
              <option value="done">done</option>
              <option value="blocked">blocked</option>
            </select>
          </div>
          {globalSearchResults.length === 0 ? (
            <p className="muted">No results for current filters.</p>
          ) : (
            <ul className="search-results">
              {globalSearchResults.map((item) => (
                <li key={item.id} className="search-item">
                  <div>
                    <strong>{item.title}</strong>
                    <p className="muted">{item.subtitle}</p>
                  </div>
                  <span
                    className={`timeline-marker ${item.kind === "task" ? "task" : "jira"}`}
                  >
                    {item.kind}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>
      {statusQuery.error ? (
        <p className="error">{String(statusQuery.error)}</p>
      ) : null}
    </section>
  );
}
