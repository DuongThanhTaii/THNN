import { useMemo, useState } from "react";

import { useAppStore } from "../shared/state/appStore";

type Device = {
  id: string;
  alias: string;
  location: string;
  online: boolean;
  battery: number;
  lastEventAt: string;
  lastEventText: string;
};

type AuditEntry = {
  id: string;
  deviceId: string;
  type: "register" | "command" | "status";
  text: string;
  at: string;
};

const commandTemplates = [
  { id: "ping", label: "Ping Device", command: "PING" },
  { id: "sync", label: "Sync Clock", command: "SYNC_TIME" },
  { id: "snapshot", label: "Capture Snapshot", command: "CAPTURE" },
  { id: "sleep", label: "Enable Sleep Mode", command: "SET_SLEEP:ON" },
];

export function DevicesPage() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const setGlobalError = useAppStore((state) => state.setGlobalError);

  const [deviceId, setDeviceId] = useState("esp32-01");
  const [alias, setAlias] = useState("Meeting Room Sensor");
  const [location, setLocation] = useState("Room A1");

  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [audit, setAudit] = useState<AuditEntry[]>([]);

  const selectedDevice = useMemo(
    () => devices.find((item) => item.id === selectedId) || devices[0],
    [devices, selectedId],
  );

  const selectedAudit = useMemo(
    () =>
      audit
        .filter((item) => item.deviceId === (selectedDevice?.id || ""))
        .slice(0, 20),
    [audit, selectedDevice?.id],
  );

  const nowLabel = () => new Date().toLocaleString();

  const appendAudit = (entry: Omit<AuditEntry, "id" | "at">) => {
    setAudit((prev) => [
      {
        ...entry,
        id: `${entry.deviceId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        at: nowLabel(),
      },
      ...prev,
    ]);
  };

  const onboardDevice = () => {
    if (!deviceId.trim()) {
      setGlobalError("Device ID is required.");
      return;
    }

    const normalizedId = deviceId.trim();
    const exists = devices.some((item) => item.id === normalizedId);
    if (exists) {
      setGlobalError(`Device ${normalizedId} already registered.`);
      return;
    }

    const next: Device = {
      id: normalizedId,
      alias: alias.trim() || normalizedId,
      location: location.trim() || "Unknown",
      online: true,
      battery: 100,
      lastEventAt: nowLabel(),
      lastEventText: "Device registered",
    };

    setDevices((prev) => [next, ...prev]);
    setSelectedId(normalizedId);
    setGlobalError("");
    appendAudit({
      deviceId: normalizedId,
      type: "register",
      text: "Onboarded device via ESP32 registration form",
    });
  };

  const sendTemplate = (command: string) => {
    if (!selectedDevice) return;

    setDevices((prev) =>
      prev.map((item) =>
        item.id === selectedDevice.id
          ? {
              ...item,
              lastEventAt: nowLabel(),
              lastEventText: `Command sent: ${command}`,
              battery:
                command === "CAPTURE"
                  ? Math.max(1, item.battery - 4)
                  : Math.max(1, item.battery - 1),
            }
          : item,
      ),
    );

    appendAudit({
      deviceId: selectedDevice.id,
      type: "command",
      text: `Template command dispatched: ${command}`,
    });
    setGlobalError("");
  };

  const toggleOnline = () => {
    if (!selectedDevice) return;

    setDevices((prev) =>
      prev.map((item) =>
        item.id === selectedDevice.id
          ? {
              ...item,
              online: !item.online,
              lastEventAt: nowLabel(),
              lastEventText: !item.online
                ? "Device reconnected"
                : "Device marked offline",
            }
          : item,
      ),
    );

    appendAudit({
      deviceId: selectedDevice.id,
      type: "status",
      text: selectedDevice.online ? "Set offline" : "Set online",
    });
  };

  return (
    <section className="stack">
      <h2>ESP32 Device Control</h2>

      <div className="card-grid">
        <article className="card stack">
          <h3>Device Onboarding</h3>
          <p className="muted">Workspace #{workspaceId}</p>
          <label className="stack compact">
            Device ID
            <input
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
            />
          </label>
          <label className="stack compact">
            Alias
            <input value={alias} onChange={(e) => setAlias(e.target.value)} />
          </label>
          <label className="stack compact">
            Location
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </label>
          <button className="btn-primary" type="button" onClick={onboardDevice}>
            Register ESP32 Device
          </button>
        </article>

        <article className="card stack">
          <h3>Device Status Panel</h3>
          {!selectedDevice ? (
            <p className="muted">No device selected.</p>
          ) : (
            <>
              <div className="device-metric-grid">
                <div className="device-metric">
                  <span
                    className={`status-dot ${selectedDevice.online ? "ok" : "off"}`}
                  />
                  <strong>
                    {selectedDevice.online ? "Online" : "Offline"}
                  </strong>
                </div>
                <div className="device-metric">
                  <strong>Battery</strong>
                  <span className="muted">{selectedDevice.battery}%</span>
                </div>
                <div className="device-metric">
                  <strong>Last Event</strong>
                  <span className="muted">{selectedDevice.lastEventAt}</span>
                </div>
              </div>
              <p className="muted">{selectedDevice.lastEventText}</p>
              <button
                className="btn-secondary"
                type="button"
                onClick={toggleOnline}
              >
                {selectedDevice.online ? "Mark Offline" : "Mark Online"}
              </button>
            </>
          )}
        </article>
      </div>

      <div className="card-grid">
        <article className="card stack">
          <h3>Quick Command Templates</h3>
          {!selectedDevice ? (
            <p className="muted">Register/select a device to send commands.</p>
          ) : (
            <div className="command-grid">
              {commandTemplates.map((template) => (
                <button
                  key={template.id}
                  className="btn-secondary"
                  type="button"
                  onClick={() => sendTemplate(template.command)}
                >
                  {template.label}
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="card stack">
          <h3>Registered Devices ({devices.length})</h3>
          {devices.length === 0 ? (
            <p className="muted">No ESP32 devices onboarded yet.</p>
          ) : (
            <ul className="policy-list">
              {devices.map((item) => (
                <li key={item.id}>
                  <div className="stack compact">
                    <strong>{item.alias}</strong>
                    <span className="muted">
                      {item.id} · {item.location}
                    </span>
                  </div>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                  >
                    {selectedDevice?.id === item.id ? "Selected" : "Select"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <article className="card stack">
        <h3>Device Command/Audit Timeline</h3>
        {!selectedDevice ? (
          <p className="muted">Select a device to view its timeline.</p>
        ) : selectedAudit.length === 0 ? (
          <p className="muted">No audit events yet.</p>
        ) : (
          <ul className="audit-list">
            {selectedAudit.map((entry) => (
              <li key={entry.id}>
                <span
                  className={`timeline-marker ${entry.type === "command" ? "jira" : entry.type === "status" ? "calendar" : "task"}`}
                >
                  {entry.type}
                </span>
                <div className="stack compact">
                  <strong>{entry.text}</strong>
                  <span className="muted">{entry.at}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}
