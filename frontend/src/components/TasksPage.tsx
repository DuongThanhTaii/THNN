import { type FormEvent, useEffect, useState } from "react";

import {
  createTask,
  deleteTask,
  listTasksFiltered,
  type Task,
  updateTask,
} from "../lib/api";

const STATUSES = ["todo", "in_progress", "done", "blocked"] as const;

export function TasksPage() {
  const [workspaceId, setWorkspaceId] = useState(1);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listTasksFiltered({
        workspaceId,
        status: statusFilter !== "all" ? statusFilter : undefined,
        q: query.trim() || undefined,
        limit,
        offset,
      });
      setTasks(data);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [workspaceId, statusFilter, query, limit, offset]);

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

  const changeStatus = async (task: Task, newStatus: string) => {
    setError("");
    try {
      await updateTask({
        taskId: task.id,
        workspace_id: workspaceId,
        status: newStatus,
      });
      await refresh();
    } catch (e: unknown) {
      setError(String(e));
    }
  };

  const removeTask = async (task: Task) => {
    setError("");
    try {
      await deleteTask({
        taskId: task.id,
        workspaceId,
      });
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
          <div className="toolbar">
            <input
              value={query}
              onChange={(e) => {
                setOffset(0);
                setQuery(e.target.value);
              }}
              placeholder="Search title or description"
            />
            <select
              value={statusFilter}
              onChange={(e) => {
                setOffset(0);
                setStatusFilter(e.target.value);
              }}
            >
              <option value="all">all</option>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <select
              value={limit}
              onChange={(e) => {
                setOffset(0);
                setLimit(Number(e.target.value || 20));
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          {loading ? <p>Loading tasks...</p> : null}
          {!loading && tasks.length === 0 ? <p>No tasks yet.</p> : null}
          {tasks.length > 0 ? (
            <ul className="list">
              {tasks.map((task) => (
                <li key={task.id}>
                  <div className="task-main">
                    <strong>{task.title}</strong>
                    <span className="muted">#{task.id}</span>
                    <span className="muted">{task.priority}</span>
                  </div>
                  <div className="task-actions">
                    <select
                      value={task.status}
                      onChange={(e) => void changeStatus(task, e.target.value)}
                    >
                      {STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn-danger"
                      type="button"
                      onClick={() => void removeTask(task)}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          <div className="toolbar">
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
            >
              Prev
            </button>
            <span className="muted">
              offset {offset} / limit {limit}
            </span>
            <button
              className="btn-secondary"
              type="button"
              onClick={() => setOffset(offset + limit)}
              disabled={tasks.length < limit}
            >
              Next
            </button>
          </div>
        </article>
      </div>

      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
