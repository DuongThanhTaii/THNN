import { useMutation } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";

import { loginAuth } from "../lib/api";
import { useAppStore } from "../shared/state/appStore";
import { useAuthStore } from "../shared/state/authStore";

export function LoginPage() {
  const setSession = useAuthStore((state) => state.setSession);
  const setGlobalError = useAppStore((state) => state.setGlobalError);
  const [email, setEmail] = useState("owner@agent.local");
  const [password, setPassword] = useState("demo-password");
  const [role, setRole] = useState<"owner" | "admin" | "member" | "viewer">(
    "owner",
  );
  const [hint, setHint] = useState("");

  const loginMutation = useMutation({
    mutationFn: loginAuth,
    onSuccess: (session) => {
      setSession(session);
      setGlobalError("");
      setHint("Signed in successfully.");
    },
    onError: (error) => {
      setGlobalError(String(error));
      setHint("");
    },
  });

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHint("");
    await loginMutation.mutateAsync({
      email: email.trim(),
      password,
      role,
    });
  };

  return (
    <section className="auth-wrap">
      <article className="auth-card stack">
        <p className="auth-kicker">Agent Platform</p>
        <h2>Welcome Back</h2>
        <p className="muted">Sign in to continue to your workspace console.</p>

        <form onSubmit={submit} className="stack">
          <label className="stack compact">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="owner@agent.local"
              required
            />
          </label>

          <label className="stack compact">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              required
            />
          </label>

          <label className="stack compact">
            Role
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as typeof role)}
            >
              <option value="owner">owner</option>
              <option value="admin">admin</option>
              <option value="member">member</option>
              <option value="viewer">viewer</option>
            </select>
          </label>

          <button
            className="btn-primary"
            type="submit"
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {hint ? <p className="auth-hint">{hint}</p> : null}
      </article>
    </section>
  );
}
