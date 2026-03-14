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

export function getJiraConnectInfo(): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>("/api/v1/integrations/jira/connect");
}

export function getGoogleConnectInfo(): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    "/api/v1/integrations/google/connect",
  );
}
