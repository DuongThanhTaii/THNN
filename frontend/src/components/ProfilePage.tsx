import { useMemo, useState } from "react";

import { useAuthStore } from "../shared/state/authStore";

type PromptMode = "reveal" | "copy" | "rotate" | "revoke";

type ApiKeyRecord = {
  id: string;
  label: string;
  prefix: string;
  lastUsedAt: string;
  createdAt: string;
  active: boolean;
};

const PROMPT_WORD: Record<PromptMode, string> = {
  reveal: "REVEAL",
  copy: "COPY",
  rotate: "ROTATE",
  revoke: "REVOKE",
};

const initialKeys: ApiKeyRecord[] = [
  {
    id: "key_prod_1",
    label: "Primary Production",
    prefix: "ag_live_7ce1",
    lastUsedAt: "2026-03-17 09:24",
    createdAt: "2026-03-11",
    active: true,
  },
  {
    id: "key_dev_1",
    label: "Local Development",
    prefix: "ag_dev_12bd",
    lastUsedAt: "2026-03-16 18:40",
    createdAt: "2026-03-08",
    active: true,
  },
];

function makeToken(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

export function ProfilePage() {
  const userEmail = useAuthStore((state) => state.userEmail);
  const role = useAuthStore((state) => state.role);

  const [displayName, setDisplayName] = useState("Agent Owner");
  const [keys, setKeys] = useState<ApiKeyRecord[]>(initialKeys);
  const [revealedKeyId, setRevealedKeyId] = useState("");
  const [revealedToken, setRevealedToken] = useState("");

  const [promptMode, setPromptMode] = useState<PromptMode | null>(null);
  const [promptKeyId, setPromptKeyId] = useState("");
  const [promptInput, setPromptInput] = useState("");

  const keyById = useMemo(
    () => Object.fromEntries(keys.map((key) => [key.id, key])),
    [keys],
  );

  const openPrompt = (mode: PromptMode, keyId: string) => {
    setPromptMode(mode);
    setPromptKeyId(keyId);
    setPromptInput("");
  };

  const closePrompt = () => {
    setPromptMode(null);
    setPromptKeyId("");
    setPromptInput("");
  };

  const onConfirmPrompt = async () => {
    if (!promptMode || !promptKeyId) return;
    const expected = PROMPT_WORD[promptMode];
    if (promptInput.trim().toUpperCase() !== expected) return;

    if (promptMode === "reveal") {
      const key = keyById[promptKeyId];
      if (!key) return;
      setRevealedKeyId(promptKeyId);
      setRevealedToken(makeToken(key.prefix));
    }

    if (promptMode === "copy") {
      if (
        typeof navigator !== "undefined" &&
        navigator.clipboard &&
        revealedToken
      ) {
        await navigator.clipboard.writeText(revealedToken);
      }
    }

    if (promptMode === "rotate") {
      setKeys((prev) =>
        prev.map((key) =>
          key.id === promptKeyId
            ? {
                ...key,
                prefix: `${key.prefix.split("_")[0]}_${Math.random()
                  .toString(36)
                  .slice(2, 6)}`,
                createdAt: new Date().toISOString().slice(0, 10),
              }
            : key,
        ),
      );
      if (revealedKeyId === promptKeyId) {
        setRevealedToken(makeToken("ag_rot"));
      }
    }

    if (promptMode === "revoke") {
      setKeys((prev) =>
        prev.map((key) =>
          key.id === promptKeyId ? { ...key, active: false } : key,
        ),
      );
      if (revealedKeyId === promptKeyId) {
        setRevealedKeyId("");
        setRevealedToken("");
      }
    }

    closePrompt();
  };

  return (
    <section className="stack">
      <h2>Profile & Security</h2>

      <div className="card-grid">
        <article className="card stack">
          <h3>Profile</h3>
          <label className="stack compact">
            Display name
            <input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>
          <label className="stack compact">
            Email
            <input value={userEmail} disabled />
          </label>
          <label className="stack compact">
            Role
            <input value={role} disabled />
          </label>
          <p className="muted">
            Sensitive fields are read-only and controlled by your auth provider.
          </p>
        </article>

        <article className="card stack">
          <h3>API Key Safety</h3>
          <p className="muted">
            Revealing, copying, rotating, or revoking an API key always requires
            explicit prompt confirmation.
          </p>
          <ul className="safety-list">
            <li>Keys are masked by default.</li>
            <li>Actions require typed confirmation words.</li>
            <li>Revoked keys are immediately disabled in this UI.</li>
          </ul>
        </article>
      </div>

      <article className="card stack">
        <h3>API Keys</h3>
        <div className="stack">
          {keys.map((key) => {
            const isRevealed = revealedKeyId === key.id;
            return (
              <div key={key.id} className="key-row">
                <div className="stack compact">
                  <strong>{key.label}</strong>
                  <span className="muted">
                    {key.active ? "active" : "revoked"}
                  </span>
                  <span className="muted">
                    Created {key.createdAt}, last used {key.lastUsedAt}
                  </span>
                  <code className="key-code">
                    {isRevealed ? revealedToken : `${key.prefix}••••••••••••••`}
                  </code>
                </div>
                <div className="task-actions">
                  <button
                    className="btn-secondary"
                    type="button"
                    disabled={!key.active}
                    onClick={() => openPrompt("reveal", key.id)}
                  >
                    Reveal
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    disabled={!key.active || !isRevealed}
                    onClick={() => openPrompt("copy", key.id)}
                  >
                    Copy
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    disabled={!key.active}
                    onClick={() => openPrompt("rotate", key.id)}
                  >
                    Rotate
                  </button>
                  <button
                    className="btn-danger"
                    type="button"
                    disabled={!key.active}
                    onClick={() => openPrompt("revoke", key.id)}
                  >
                    Revoke
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </article>

      {promptMode ? (
        <div className="prompt-backdrop" role="dialog" aria-modal="true">
          <article className="prompt-card stack">
            <h3>Security Confirmation</h3>
            <p className="muted">
              Type <strong>{PROMPT_WORD[promptMode]}</strong> to continue this
              sensitive action.
            </p>
            <input
              value={promptInput}
              onChange={(event) => setPromptInput(event.target.value)}
              placeholder={PROMPT_WORD[promptMode]}
            />
            <div className="task-actions">
              <button
                className="btn-secondary"
                type="button"
                onClick={closePrompt}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                type="button"
                onClick={() => void onConfirmPrompt()}
              >
                Confirm
              </button>
            </div>
          </article>
        </div>
      ) : null}
    </section>
  );
}
