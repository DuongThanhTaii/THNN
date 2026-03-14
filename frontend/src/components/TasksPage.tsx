import { type FormEvent, useEffect, useState } from "react";

import { createTask, listTasks, type Task } from "../lib/api";

export function TasksPage() {
  const [workspaceId, setWorkspaceId] = useState(1);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listTasks(workspaceId);
      setTasks(data);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [workspaceId]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) return;

    setError("");
    try {
      await createTask({
        workspace_id: workspaceId,
        title: title.trim(),
        description: description.trim() || undefined,
      });
      setTitle("");
      setDescription("");
      await refresh();
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  return (
    <section className="stack">
      <h2>Tasks</h2>

      <div className="card-grid">
        <article className="card">
          <h3>Create Task</h3>
          <form onSubmit={submit} className="stack">
            <label className="stack compact">
              Workspace ID
              <input
                type="number"
                min={1}
                value={workspaceId}
                onChange={(e) => setWorkspaceId(Number(e.target.value || 1))}
              />
            </label>
            <label className="stack compact">
              Title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Prepare sprint plan"
              />
            </label>
            <label className="stack compact">
              Description
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional details"
              />
            </label>
            <button className="btn-primary" type="submit">
              Save Task
            </button>
          </form>
        </article>

        <article className="card">
          <h3>Task List</h3>
          {loading ? <p>Loading tasks...</p> : null}
          {!loading && tasks.length === 0 ? <p>No tasks yet.</p> : null}
          {tasks.length > 0 ? (
            <ul className="list">
              {tasks.map((task) => (
                <li key={task.id}>
                  <strong>{task.title}</strong>
                  <span className="muted">#{task.id}</span>
                  <span>{task.status}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </article>
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
