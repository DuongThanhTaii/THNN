const WS_BASE =
  import.meta.env.VITE_WS_BASE_URL?.replace(/\/+$/, "") ||
  "ws://localhost:8082";

export type WsConnection = {
  socket: WebSocket;
  close: () => void;
};

export function connectWorkspaceSocket(
  workspaceId: number,
  onOpen: () => void,
  onClose: () => void,
  onError: (message: string) => void,
): WsConnection {
  const socket = new WebSocket(
    `${WS_BASE}/ws/workspaces/${encodeURIComponent(String(workspaceId))}`,
  );

  socket.addEventListener("open", onOpen);
  socket.addEventListener("close", onClose);
  socket.addEventListener("error", () => onError("WebSocket connection error"));

  return {
    socket,
    close: () => socket.close(),
  };
}
