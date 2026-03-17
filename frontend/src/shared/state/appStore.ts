import { create } from "zustand";

export type WsState = "disconnected" | "connected" | "error";

type AppState = {
  workspaceId: number;
  wsState: WsState;
  globalError: string;
  setWorkspaceId: (workspaceId: number) => void;
  setWsState: (wsState: WsState) => void;
  setGlobalError: (globalError: string) => void;
};

export const useAppStore = create<AppState>((set) => ({
  workspaceId: 1,
  wsState: "disconnected",
  globalError: "",
  setWorkspaceId: (workspaceId) => set({ workspaceId }),
  setWsState: (wsState) => set({ wsState }),
  setGlobalError: (globalError) => set({ globalError }),
}));
