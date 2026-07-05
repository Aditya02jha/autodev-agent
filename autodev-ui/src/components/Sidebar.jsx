const NAV = [
  { id: "sandbox", icon: "⚡", label: "Sandbox" },
  { id: "history", icon: "🕓", label: "History" },
  { id: "ask", icon: "💬", label: "Ask codebase" },
];

export default function Sidebar({ view, setView, indexed }) {
  async function reindex() {
    try {
      await fetch("http://localhost:8000/index", { method: "POST" });
      alert("Re-indexed.");
    } catch {
      alert("Could not reach server at localhost:8000");
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
