import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  createAutomation,
  deleteAutomation,
  getSyncStatus,
  listAutomations,
  type SyncConflictSummary,
} from "../lib/api";
import { useAppStore } from "../shared/state/appStore";
import { useAuthStore } from "../shared/state/authStore";

type SyncPolicy = {
  id: string;
  source: string;
  target: string;
  mapping: string;
  precedence: "source" | "target" | "manual";
  enabled: boolean;
};

type ResolutionAction = {
  id: string;
  conflictId: number;
  strategy: "manual" | "last-write-wins" | "source-of-truth";
  at: string;
};

type RetryItem = {
  id: string;
  channel: string;
  status: "pending" | "retrying" | "dead_letter" | "resolved";
  attempts: number;
};

const defaultPolicies: SyncPolicy[] = [
  {
    id: "p-jira-gcal",
    source: "jira.issue",
    target: "google_calendar.event",
    mapping: "summary->title, due_date->start/end",
    precedence: "source",
    enabled: true,
  },
  {
    id: "p-gcal-jira",
    source: "google_calendar.event",
    target: "jira.issue",
    mapping: "title->summary, location->description",
    precedence: "manual",
    enabled: false,
  },
];

const defaultRetryItems: RetryItem[] = [
  { id: "r1", channel: "jira.webhook", status: "pending", attempts: 0 },
  {
    id: "r2",
    channel: "google.webhook",
    status: "retrying",
    attempts: 2,
  },
  { id: "r3", channel: "sync.mapper", status: "dead_letter", attempts: 5 },
];

export function AutomationPage() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const setGlobalError = useAppStore((state) => state.setGlobalError);
  const role = useAuthStore((state) => state.role);

  const canEdit = role !== "viewer";

  const queryClient = useQueryClient();
  const [ruleName, setRuleName] = useState("Daily Jira to Calendar Sync");
  const [triggerType, setTriggerType] = useState("schedule");
  const [actionType, setActionType] = useState("sync_bidirectional");
  const [schedule, setSchedule] = useState("0 8 * * *");
  const [policies, setPolicies] = useState<SyncPolicy[]>(defaultPolicies);
  const [resolutionHistory, setResolutionHistory] = useState<
    ResolutionAction[]
  >([]);
  const [retryItems, setRetryItems] = useState<RetryItem[]>(defaultRetryItems);

  const automationsQuery = useQuery({
    queryKey: ["automations", workspaceId],
    queryFn: () => listAutomations({ workspaceId, limit: 100, offset: 0 }),
    enabled: workspaceId > 0,
  });

  const syncStatusQuery = useQuery({
    queryKey: ["sync-status", workspaceId],
    queryFn: () => getSyncStatus({ workspaceId, recentLimit: 15 }),
    enabled: workspaceId > 0,
  });

  const createMutation = useMutation({
    mutationFn: createAutomation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["automations", workspaceId],
      });
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAutomation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["automations", workspaceId],
      });
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const submitRule = async () => {
    if (!ruleName.trim() || !canEdit) return;
    await createMutation.mutateAsync({
      workspace_id: workspaceId,
      name: ruleName.trim(),
      trigger_type: triggerType,
      action_type: actionType,
      enabled: true,
      config: {
        schedule,
        source: "jira",
        target: "google_calendar",
      },
    });
  };

  const resolveConflict = (
    conflict: SyncConflictSummary,
    strategy: ResolutionAction["strategy"],
  ) => {
    const action: ResolutionAction = {
      id: `${conflict.id}-${Date.now()}`,
      conflictId: conflict.id,
      strategy,
      at: new Date().toLocaleString(),
    };
    setResolutionHistory((prev) => [action, ...prev].slice(0, 20));
  };

  const cycleRetry = (itemId: string) => {
    setRetryItems((prev) =>
      prev.map((item) => {
        if (item.id !== itemId) return item;
        if (item.status === "dead_letter") return item;
        if (item.status === "pending") {
          return { ...item, status: "retrying", attempts: item.attempts + 1 };
        }
        if (item.attempts >= 4) {
          return {
            ...item,
            status: "dead_letter",
            attempts: item.attempts + 1,
          };
        }
        return { ...item, status: "resolved", attempts: item.attempts + 1 };
      }),
    );
  };

  const deadLetterCount = useMemo(
    () => retryItems.filter((item) => item.status === "dead_letter").length,
    [retryItems],
  );

  return (
    <section className="stack">
      <h2>Automation & Sync Control</h2>

      <div className="card-grid">
        <article className="card stack">
          <h3>Automation Rule Builder</h3>
          <label className="stack compact">
            Rule name
            <input
              value={ruleName}
              onChange={(e) => setRuleName(e.target.value)}
            />
          </label>
          <div className="toolbar">
            <label className="stack compact">
              Trigger
              <select
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value)}
              >
                <option value="schedule">schedule</option>
                <option value="event">event</option>
                <option value="manual">manual</option>
              </select>
            </label>
            <label className="stack compact">
              Action
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
              >
                <option value="sync_bidirectional">sync_bidirectional</option>
                <option value="create_task">create_task</option>
                <option value="notify">notify</option>
              </select>
            </label>
          </div>
          <label className="stack compact">
            Schedule (cron)
            <input
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
            />
          </label>
          <button
            className="btn-primary"
            type="button"
            onClick={() => void submitRule()}
            disabled={!canEdit || createMutation.isPending}
          >
            {createMutation.isPending ? "Saving..." : "Save Automation Rule"}
          </button>
        </article>

        <article className="card stack">
          <h3>Sync Policy Editor</h3>
          <p className="muted">
            Edit mapping and precedence for sync policies.
          </p>
          <ul className="policy-list">
            {policies.map((policy) => (
              <li key={policy.id}>
                <div className="stack compact">
                  <strong>
                    {policy.source} {" -> "} {policy.target}
                  </strong>
                  <span className="muted">{policy.mapping}</span>
                </div>
                <div className="task-actions">
                  <select
                    value={policy.precedence}
                    onChange={(e) =>
                      setPolicies((prev) =>
                        prev.map((item) =>
                          item.id === policy.id
                            ? {
                                ...item,
                                precedence: e.target
                                  .value as SyncPolicy["precedence"],
                              }
                            : item,
                        ),
                      )
                    }
                  >
                    <option value="source">source-of-truth: source</option>
                    <option value="target">source-of-truth: target</option>
                    <option value="manual">manual review</option>
                  </select>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() =>
                      setPolicies((prev) =>
                        prev.map((item) =>
                          item.id === policy.id
                            ? { ...item, enabled: !item.enabled }
                            : item,
                        ),
                      )
                    }
                  >
                    {policy.enabled ? "Disable" : "Enable"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <div className="card-grid">
        <article className="card stack">
          <h3>Conflict Resolution Center</h3>
          <p className="muted">
            Open conflicts: {syncStatusQuery.data?.conflicts_open ?? 0},
            resolved: {syncStatusQuery.data?.conflicts_resolved ?? 0}
          </p>
          <ul className="policy-list">
            {(syncStatusQuery.data?.recent_conflicts || []).map((conflict) => (
              <li key={conflict.id}>
                <div className="stack compact">
                  <strong>
                    #{conflict.id} {conflict.source_system} {" -> "}{" "}
                    {conflict.target_system}
                  </strong>
                  <span className="muted">{conflict.reason}</span>
                  <span className="muted">status: {conflict.status}</span>
                </div>
                <div className="task-actions">
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => resolveConflict(conflict, "manual")}
                  >
                    Manual
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => resolveConflict(conflict, "last-write-wins")}
                  >
                    Last Write Wins
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => resolveConflict(conflict, "source-of-truth")}
                  >
                    Source of Truth
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {resolutionHistory.length > 0 ? (
            <pre>{JSON.stringify(resolutionHistory, null, 2)}</pre>
          ) : null}
        </article>

        <article className="card stack">
          <h3>Retry / Dead-letter Inspector</h3>
          <p className="muted">Dead-letter queue size: {deadLetterCount}</p>
          <ul className="policy-list">
            {retryItems.map((item) => (
              <li key={item.id}>
                <div className="stack compact">
                  <strong>{item.channel}</strong>
                  <span className="muted">
                    status: {item.status} / attempts: {item.attempts}
                  </span>
                </div>
                <button
                  className="btn-secondary"
                  type="button"
                  disabled={item.status === "dead_letter"}
                  onClick={() => cycleRetry(item.id)}
                >
                  Retry Once
                </button>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <article className="card stack">
        <h3>Saved Automations ({automationsQuery.data?.length ?? 0})</h3>
        {!automationsQuery.data || automationsQuery.data.length === 0 ? (
          <p className="muted">No automation rules created yet.</p>
        ) : (
          <ul className="policy-list">
            {automationsQuery.data.map((item) => (
              <li key={item.id}>
                <div className="stack compact">
                  <strong>{item.name}</strong>
                  <span className="muted">
                    {item.trigger_type} {" -> "} {item.action_type}
                  </span>
                </div>
                <button
                  className="btn-danger"
                  type="button"
                  disabled={deleteMutation.isPending || !canEdit}
                  onClick={() =>
                    void deleteMutation.mutateAsync({
                      automationId: item.id,
                      workspaceId,
                    })
                  }
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
