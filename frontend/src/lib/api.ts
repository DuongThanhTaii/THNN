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

export type LoginInput = {
  email: string;
  password: string;
  role: "owner" | "admin" | "member" | "viewer";
};

export type RefreshInput = {
  refreshToken: string;
  userEmail: string;
  role: "owner" | "admin" | "member" | "viewer";
};

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  userEmail: string;
  role: "owner" | "admin" | "member" | "viewer";
};

export type Workspace = {
  id: number;
  slug: string;
  name: string;
  owner_user_id: number | null;
};

export type Automation = {
  id: number;
  workspace_id: number;
  name: string;
  trigger_type: string;
  action_type: string;
  config: Record<string, unknown>;
  enabled: boolean;
};

export type SyncConflictSummary = {
  id: number;
  source_system: string;
  target_system: string;
  entity_ref: string;
  reason: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
};

export type SyncStatusProjection = {
  workspace_id: number;
  health: string;
  policies_total: number;
  policies_enabled: number;
  conflicts_open: number;
  conflicts_resolved: number;
  last_conflict_at: string | null;
  recent_conflicts: SyncConflictSummary[];
};

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://localhost:8082";

function loadPersistedAccessToken(): string {
  if (typeof window === "undefined") return "";

  const raw = window.localStorage.getItem("agent-auth");
  if (!raw) return "";

  try {
    const parsed = JSON.parse(raw) as {
      state?: { accessToken?: string };
    };
    return parsed.state?.accessToken || "";
  } catch {
    return "";
  }
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function fallbackToken(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 12)}`;
}

function parseAuthSession(data: unknown, fallbackEmail: string): AuthSession {
  const payload = (data && typeof data === "object" ? data : {}) as Record<
    string,
    unknown
  >;

  const accessToken =
    asString(payload.access_token) ||
    asString(payload.accessToken) ||
    fallbackToken("access");

  const refreshToken =
    asString(payload.refresh_token) ||
    asString(payload.refreshToken) ||
    fallbackToken("refresh");

  const expiresAtCandidate =
    asString(payload.expires_at) || asString(payload.expiresAt);

  const expiresAt =
    expiresAtCandidate || new Date(Date.now() + 15 * 60_000).toISOString();
  const userEmail =
    asString(payload.email) || fallbackEmail || "owner@agent.local";
  const roleCandidate = asString(payload.role).toLowerCase();
  const role =
    roleCandidate === "owner" ||
    roleCandidate === "admin" ||
    roleCandidate === "member" ||
    roleCandidate === "viewer"
      ? roleCandidate
      : "owner";

  return {
    accessToken,
    refreshToken,
    expiresAt,
    userEmail,
    role,
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const authToken = loadPersistedAccessToken();

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(authToken ? { authorization: `Bearer ${authToken}` } : {}),
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

export function getJiraConnectInfo(
  workspaceId = 1,
): Promise<Record<string, unknown>> {
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

export async function loginAuth(input: LoginInput): Promise<AuthSession> {
  const response = await requestJson<Record<string, unknown>>(
    "/api/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({
        email: input.email,
        password: input.password,
        role: input.role,
      }),
    },
  );

  const session = parseAuthSession(response, input.email);
  return {
    ...session,
    role: input.role || session.role,
  };
}

export async function refreshAuth(input: RefreshInput): Promise<AuthSession> {
  const response = await requestJson<Record<string, unknown>>(
    "/api/v1/auth/refresh",
    {
      method: "POST",
      body: JSON.stringify({
        refresh_token: input.refreshToken,
      }),
    },
  );

  const session = parseAuthSession(response, input.userEmail);
  return {
    ...session,
    role: input.role || session.role,
  };
}

export function listWorkspaces(): Promise<Workspace[]> {
  return requestJson<Workspace[]>("/api/v1/workspaces?limit=100&offset=0");
}

export function listAutomations(input: {
  workspaceId: number;
  enabled?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Automation[]> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(input.workspaceId));
  if (typeof input.enabled === "boolean") {
    params.set("enabled", String(input.enabled));
  }
  if (typeof input.limit === "number") params.set("limit", String(input.limit));
  if (typeof input.offset === "number")
    params.set("offset", String(input.offset));

  return requestJson<Automation[]>(`/api/v1/automations?${params.toString()}`);
}

export function createAutomation(input: {
  workspace_id: number;
  name: string;
  trigger_type: string;
  action_type: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}): Promise<Automation> {
  return requestJson<Automation>("/api/v1/automations", {
    method: "POST",
    body: JSON.stringify({
      ...input,
      config: input.config || {},
      enabled: typeof input.enabled === "boolean" ? input.enabled : true,
    }),
  });
}

export function updateAutomation(input: {
  automationId: number;
  workspace_id: number;
  name?: string;
  trigger_type?: string;
  action_type?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}): Promise<Automation> {
  const payload: Record<string, unknown> = {
    workspace_id: input.workspace_id,
  };
  if (typeof input.name === "string") payload.name = input.name;
  if (typeof input.trigger_type === "string")
    payload.trigger_type = input.trigger_type;
  if (typeof input.action_type === "string")
    payload.action_type = input.action_type;
  if (input.config) payload.config = input.config;
  if (typeof input.enabled === "boolean") payload.enabled = input.enabled;

  return requestJson<Automation>(`/api/v1/automations/${input.automationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAutomation(input: {
  automationId: number;
  workspaceId: number;
}): Promise<{ status: string; deleted: number }> {
  return requestJson<{ status: string; deleted: number }>(
    `/api/v1/automations/${input.automationId}?workspace_id=${input.workspaceId}`,
    { method: "DELETE" },
  );
}

export function getSyncStatus(input: {
  workspaceId: number;
  recentLimit?: number;
}): Promise<SyncStatusProjection> {
  const params = new URLSearchParams();
  params.set("workspace_id", String(input.workspaceId));
  if (typeof input.recentLimit === "number") {
    params.set("recent_limit", String(input.recentLimit));
  }
  return requestJson<SyncStatusProjection>(
    `/api/v1/sync/status?${params.toString()}`,
  );
}
