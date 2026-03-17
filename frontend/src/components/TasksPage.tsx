import { type FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createTask,
  deleteTask,
  listTasksFiltered,
  type Task,
  updateTask,
} from "../lib/api";
import { useAppStore } from "../shared/state/appStore";

const STATUSES = ["todo", "in_progress", "done", "blocked"] as const;

export function TasksPage() {
  const workspaceId = useAppStore((state) => state.workspaceId);
  const setWorkspaceId = useAppStore((state) => state.setWorkspaceId);
  const setGlobalError = useAppStore((state) => state.setGlobalError);

  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"list" | "kanban">("kanban");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const queryClient = useQueryClient();

  const tasksQuery = useQuery<Task[]>({
    queryKey: ["tasks", workspaceId, statusFilter, query, limit, offset],
    queryFn: () =>
      listTasksFiltered({
        workspaceId,
        status: statusFilter !== "all" ? statusFilter : undefined,
        q: query.trim() || undefined,
        limit,
        offset,
      }),
  });

  const createTaskMutation = useMutation({
    mutationFn: createTask,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const updateTaskMutation = useMutation({
    mutationFn: updateTask,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const deleteTaskMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setGlobalError("");
    },
    onError: (error) => setGlobalError(String(error)),
  });

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) return;

    await createTaskMutation.mutateAsync({
      workspace_id: workspaceId,
      title: title.trim(),
      description: description.trim() || undefined,
    });
    setTitle("");
    setDescription("");
  };

  const changeStatus = async (task: Task, newStatus: string) => {
    await updateTaskMutation.mutateAsync({
      taskId: task.id,
      workspace_id: workspaceId,
      status: newStatus,
    });
  };

  const removeTask = async (task: Task) => {
    await deleteTaskMutation.mutateAsync({
      taskId: task.id,
      workspaceId,
    });
  };

  useEffect(() => {
    if (tasksQuery.error) {
      setGlobalError(String(tasksQuery.error));
    }
  }, [setGlobalError, tasksQuery.error]);

  const tasks = tasksQuery.data ?? [];
  const loading = tasksQuery.isFetching;
  const kanbanColumns = STATUSES.map((status) => ({
    status,
    items: tasks.filter((task) => task.status === status),
  }));

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
              {createTaskMutation.isPending ? "Saving..." : "Save Task"}
            </button>
          </form>
        </article>

        <article className="card">
          <h3>Task Board</h3>
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
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value as "list" | "kanban")}
            >
              <option value="kanban">kanban</option>
              <option value="list">list</option>
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
          {tasks.length > 0 && viewMode === "list" ? (
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
                      disabled={deleteTaskMutation.isPending}
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {tasks.length > 0 && viewMode === "kanban" ? (
            <div className="kanban-board">
              {kanbanColumns.map((column) => (
                <section key={column.status} className="kanban-column">
                  <header className="kanban-header">
                    <strong>{column.status}</strong>
                    <span className="muted">{column.items.length}</span>
                  </header>
                  <div className="kanban-items">
                    {column.items.length === 0 ? (
                      <p className="muted">No tasks</p>
                    ) : (
                      column.items.map((task) => (
                        <article
                          key={task.id}
                          className="kanban-card stack compact"
                        >
                          <div className="task-main">
                            <strong>{task.title}</strong>
                            <span className="muted">#{task.id}</span>
                          </div>
                          <p className="muted">
                            {task.description || "No description"}
                          </p>
                          <div className="task-actions">
                            <select
                              value={task.status}
                              onChange={(e) =>
                                void changeStatus(task, e.target.value)
                              }
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
                              disabled={deleteTaskMutation.isPending}
                            >
                              Delete
                            </button>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </section>
              ))}
            </div>
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
    </section>
  );
}
