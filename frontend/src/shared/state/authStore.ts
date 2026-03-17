import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AuthSession = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  userEmail: string;
  role: "owner" | "admin" | "member" | "viewer";
};

type AuthState = {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  userEmail: string;
  role: "owner" | "admin" | "member" | "viewer";
  isAuthenticated: boolean;
  setSession: (session: AuthSession) => void;
  logout: () => void;
};

const initialState = {
  accessToken: "",
  refreshToken: "",
  expiresAt: "",
  userEmail: "",
  role: "viewer" as const,
  isAuthenticated: false,
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      ...initialState,
      setSession: (session) =>
        set({
          accessToken: session.accessToken,
          refreshToken: session.refreshToken,
          expiresAt: session.expiresAt,
          userEmail: session.userEmail,
          role: session.role,
          isAuthenticated: true,
        }),
      logout: () => set(initialState),
    }),
    {
      name: "agent-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        userEmail: state.userEmail,
        role: state.role,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
