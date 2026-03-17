import type { ReactNode } from "react";

import { useAuthStore } from "../shared/state/authStore";

type Role = "owner" | "admin" | "member" | "viewer";

type ProtectedRouteProps = {
  children: ReactNode;
  allowedRoles: Role[];
};

export function ProtectedRoute({
  children,
  allowedRoles,
}: ProtectedRouteProps) {
  const role = useAuthStore((state) => state.role);

  if (!allowedRoles.includes(role)) {
    return (
      <section className="stack">
        <article className="card">
          <h3>Access Denied</h3>
          <p className="muted">
            Your current role does not have permission to access this screen.
          </p>
        </article>
      </section>
    );
  }

  return <>{children}</>;
}
