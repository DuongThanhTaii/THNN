export type SystemStatus = {
  status: string;
  db_connected: boolean;
  provider: string;
  environment: string;
};

export type DemoBootstrap = {
  user_id: number;
  workspace_id: number;
  workspace_slug: string;
  workspace_name: string;
};

export type Task = {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  status: string;
  priority: string;
};

export type IntegrationAccount = {
  id: number;
  provider: string;
  account_label: string;
  token_expires_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type IntegrationAccountsResponse = {
  workspace_id: number;
  count: number;
  items: IntegrationAccount[];
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://localhost:8082";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export function getSystemStatus(): Promise<SystemStatus> {
  return requestJson<SystemStatus>("/api/v1/system/status");
}

export function bootstrapDemoWorkspace(): Promise<DemoBootstrap> {
  return requestJson<DemoBootstrap>("/api/v1/system/bootstrap-demo", {
    method: "POST",
  });
}

export function listTasks(workspaceId: number): Promise<Task[]> {
  return requestJson<Task[]>(`/api/v1/tasks?workspace_id=${workspaceId}`);
}

export function listTasksFiltered(input: {
  workspaceId: number;
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<Task[]> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(input.workspaceId));
  if (input.status) params.set("status", input.status);
  if (input.q) params.set("q", input.q);
  if (typeof input.limit === "number") params.set("limit", String(input.limit));
  if (typeof input.offset === "number")
    params.set("offset", String(input.offset));

  return requestJson<Task[]>(`/api/v1/tasks?${params.toString()}`);
}

export function createTask(input: {
  workspace_id: number;
  title: string;
  description?: string;
}): Promise<Task> {
  return requestJson<Task>("/api/v1/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateTask(input: {
  taskId: number;
  workspace_id: number;
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
}): Promise<Task> {
  const payload: Record<string, unknown> = {
    workspace_id: input.workspace_id,
  };
  if (typeof input.title === "string") payload.title = input.title;
  if (typeof input.description === "string")
    payload.description = input.description;
  if (typeof input.status === "string") payload.status = input.status;
  if (typeof input.priority === "string") payload.priority = input.priority;

  return requestJson<Task>(`/api/v1/tasks/${input.taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTask(input: {
  taskId: number;
  workspaceId: number;
}): Promise<{ status: string; deleted: number }> {
  return requestJson<{ status: string; deleted: number }>(
    `/api/v1/tasks/${input.taskId}?workspace_id=${input.workspaceId}`,
    {
      method: "DELETE",
    },
  );
}

export function getJiraConnectInfo(workspaceId = 1): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(workspaceId));

  return requestJson<Record<string, unknown>>(
    `/api/v1/integrations/jira/connect?${params.toString()}`,
    { method: "POST" },
  );
}

export function getGoogleConnectInfo(
  workspaceId = 1,
): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(workspaceId));

  return requestJson<Record<string, unknown>>(
    `/api/v1/integrations/google/connect?${params.toString()}`,
    { method: "POST" },
  );
}

export function simulateJiraCallback(input: {
  workspaceId: number;
  code: string;
  state?: string;
}): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(input.workspaceId));
  params.set("code", input.code);
  if (input.state) params.set("state", input.state);

  return requestJson<Record<string, unknown>>(
    `/api/v1/integrations/jira/callback?${params.toString()}`,
  );
}

export function simulateGoogleCallback(input: {
  workspaceId: number;
  code: string;
  state?: string;
}): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(input.workspaceId));
  params.set("code", input.code);
  if (input.state) params.set("state", input.state);

  return requestJson<Record<string, unknown>>(
    `/api/v1/integrations/google/callback?${params.toString()}`,
  );
}

export function listIntegrationAccounts(
  workspaceId: number,
): Promise<IntegrationAccountsResponse> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(workspaceId));

  return requestJson<IntegrationAccountsResponse>(
    `/api/v1/integrations/accounts?${params.toString()}`,
  );
}
