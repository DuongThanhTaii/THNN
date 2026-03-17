import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { AutomationPage } from "./components/AutomationPage";
import { DashboardPage } from "./components/DashboardPage";
import { DevicesPage } from "./components/DevicesPage";
import { IntegrationsPage } from "./components/IntegrationsPage";
import { LoginPage } from "./components/LoginPage";
import { ProfilePage } from "./components/ProfilePage";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { TasksPage } from "./components/TasksPage";
import { listWorkspaces, refreshAuth } from "./lib/api";
import { useAppStore } from "./shared/state/appStore";
import { useAuthStore } from "./shared/state/authStore";

export function App() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const setWorkspaceId = useAppStore((state) => state.setWorkspaceId);
  const wsState = useAppStore((state) => state.wsState);
  const globalError = useAppStore((state) => state.globalError);
  const setGlobalError = useAppStore((state) => state.setGlobalError);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const userEmail = useAuthStore((state) => state.userEmail);
  const role = useAuthStore((state) => state.role);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const expiresAt = useAuthStore((state) => state.expiresAt);
  const setSession = useAuthStore((state) => state.setSession);
  const logout = useAuthStore((state) => state.logout);

  const workspacesQuery = useQuery({
    queryKey: ["workspaces"],
    queryFn: listWorkspaces,
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (!workspacesQuery.data || workspacesQuery.data.length === 0) return;

    const exists = workspacesQuery.data.some(
      (workspace) => workspace.id === workspaceId,
    );
    if (!exists) {
      setWorkspaceId(workspacesQuery.data[0].id);
    }
  }, [setWorkspaceId, workspaceId, workspacesQuery.data]);

  const refreshMutation = useMutation({
    mutationFn: refreshAuth,
    onSuccess: (session) => {
      setSession(session);
      setGlobalError("");
    },
    onError: () => {
      logout();
      setGlobalError("Session expired. Please sign in again.");
    },
  });

  useEffect(() => {
    if (!isAuthenticated || !refreshToken || !expiresAt) return;

    const expiresAtMs = new Date(expiresAt).getTime();
    const delayMs = Math.max(5_000, expiresAtMs - Date.now() - 30_000);

    const timer = window.setTimeout(() => {
      void refreshMutation.mutateAsync({
        refreshToken,
        userEmail,
        role,
      });
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [
    expiresAt,
    isAuthenticated,
    refreshMutation,
    refreshToken,
    role,
    setSession,
    userEmail,
  ]);

  if (!isAuthenticated) {
    return (
      <div className="app-shell">
        <div className="window-frame auth-frame">
          <LoginPage />
        </div>
        <div className="ambient ambient-1" aria-hidden />
        <div className="ambient ambient-2" aria-hidden />
        <div className="ambient ambient-3" aria-hidden />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="window-frame">
        <header className="topbar">
          <div className="window-controls" aria-hidden>
            <span className="dot dot-red" />
            <span className="dot dot-yellow" />
            <span className="dot dot-green" />
          </div>
          <div className="topbar-meta">
            <strong>Agent Workspace</strong>
            <span>Workspace #{workspaceId}</span>
          </div>
          <div className="topbar-actions">
            <select
              value={workspaceId}
              onChange={(event) =>
                setWorkspaceId(Number(event.target.value || 1))
              }
              aria-label="Workspace switcher"
              className="workspace-switch"
            >
              {(workspacesQuery.data || []).map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
            <span className={`pill ${wsState}`}>socket: {wsState}</span>
            <span className="user-chip">
              {userEmail} ({role})
            </span>
            <button className="btn-secondary" type="button" onClick={logout}>
              Sign Out
            </button>
          </div>
        </header>

        <div className="layout">
          <aside className="sidebar">
            <h1>Command Studio</h1>
            <nav>
              <NavLink
                to="/"
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                Dashboard
              </NavLink>
              <NavLink
                to="/tasks"
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                Tasks
              </NavLink>
              <NavLink
                to="/devices"
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                Devices
              </NavLink>
              {role !== "viewer" && (
                <NavLink
                  to="/automation"
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  Automation
                </NavLink>
              )}
              {role !== "viewer" && (
                <NavLink
                  to="/integrations"
                  className={({ isActive }) => (isActive ? "active" : "")}
                >
                  Integrations
                </NavLink>
              )}
              <NavLink
                to="/profile"
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                Profile
              </NavLink>
            </nav>
          </aside>

          <main className="content">
            {globalError ? <p className="error-banner">{globalError}</p> : null}
            <Routes>
              <Route
                path="/"
                element={
                  <ProtectedRoute
                    allowedRoles={["owner", "admin", "member", "viewer"]}
                  >
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/tasks"
                element={
                  <ProtectedRoute
                    allowedRoles={["owner", "admin", "member", "viewer"]}
                  >
                    <TasksPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/devices"
                element={
                  <ProtectedRoute
                    allowedRoles={["owner", "admin", "member", "viewer"]}
                  >
                    <DevicesPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/integrations"
                element={
                  <ProtectedRoute allowedRoles={["owner", "admin", "member"]}>
                    <IntegrationsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/automation"
                element={
                  <ProtectedRoute allowedRoles={["owner", "admin", "member"]}>
                    <AutomationPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute
                    allowedRoles={["owner", "admin", "member", "viewer"]}
                  >
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      <div className="ambient ambient-1" aria-hidden />
      <div className="ambient ambient-2" aria-hidden />
      <div className="ambient ambient-3" aria-hidden />
    </div>
  );
}
