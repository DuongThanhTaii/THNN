const WS_BASE =
  import.meta.env.VITE_WS_BASE_URL?.replace(/\/+$/, "") ||
  "ws://localhost:8082";

export type RealtimeMessage = {
  type: string;
  workspace_id?: number;
  event_type?: string;
  timestamp?: number;
  payload?: unknown;
  message?: string;
};

export type WsConnection = {
  socket: WebSocket;
  close: () => void;
};

export function connectWorkspaceSocket(
  workspaceId: number,
  onOpen: () => void,
  onClose: () => void,
  onError: (message: string) => void,
  onMessage?: (message: RealtimeMessage) => void,
): WsConnection {
  const socket = new WebSocket(
    `${WS_BASE}/ws/workspaces/${encodeURIComponent(String(workspaceId))}`,
  );

  socket.addEventListener("open", onOpen);
  socket.addEventListener("close", onClose);
  socket.addEventListener("error", () => onError("WebSocket connection error"));
  socket.addEventListener("message", (event) => {
    try {
      const parsed = JSON.parse(String(event.data));
      if (parsed && typeof parsed === "object") {
        onMessage?.(parsed as RealtimeMessage);
      }
    } catch {
      // Ignore malformed socket messages in client UI.
    }
  });

  return {
    socket,
    close: () => socket.close(),
  };
}
