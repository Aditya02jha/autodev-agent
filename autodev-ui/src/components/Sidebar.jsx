import { api } from "../lib/api";

const NAV = [
  { id: "sandbox", icon: "⚡", label: "Sandbox" },
  { id: "history", icon: "🕓", label: "History" },
  { id: "ask", icon: "💬", label: "Ask codebase" },
];

export default function Sidebar({ view, setView, indexed }) {
  async function reindex() {
    try {
      await api.post("/index");
      alert("Re-indexed.");
    } catch (e) {
      alert(e.message || "Could not reach the AutoDev server");
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-icon">⚙</span>
        <span className="brand-name">AutoDev</span>
      </div>

      <nav className="sidebar-nav">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${view === item.id ? "active" : ""}`}
            onClick={() => setView(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className={`index-status ${indexed ? "ok" : "warn"}`}>
          <span className="status-dot" />
          {indexed ? "Indexed" : "Not indexed"}
        </div>
        <button className="btn-ghost small" onClick={reindex}>
          ↺ Re-index
        </button>
      </div>
    </aside>
  );
}
