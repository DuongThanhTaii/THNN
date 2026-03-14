import { Link, Route, Routes } from "react-router-dom";

import { DashboardPage } from "./components/DashboardPage";
import { IntegrationsPage } from "./components/IntegrationsPage";
import { TasksPage } from "./components/TasksPage";

export function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Agent Console</h1>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/tasks">Tasks</Link>
          <Link to="/integrations">Integrations</Link>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/integrations" element={<IntegrationsPage />} />
        </Routes>
      </main>
    </div>
  );
}
