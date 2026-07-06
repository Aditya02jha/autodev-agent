import { useApp } from "../context/AppContext";

export default function HistoryView() {
  const { history, historyLoaded, refreshHistory, clearHistory } = useApp();

  if (!historyLoaded) {
    return (
      <div className="empty-state">
        <div className="empty-title">Loading history…</div>
      </div>
    );
  }

  if (!history.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🕓</div>
        <div className="empty-title">No executions yet</div>
        <div className="empty-body">
          Run a task in Sandbox and applied changes will appear here.
        </div>
      </div>
    );
  }

  return (
    <div className="history-view">
      <div className="view-header">
        <h2>Execution history</h2>
        <span className="fl-count">{history.length} runs</span>
        <div style={{ flex: 1 }} />
        <button className="btn-ghost small" onClick={refreshHistory} title="Refresh from server">
          ↺ Refresh
        </button>
        <button className="btn-ghost small" onClick={clearHistory} title="Clear all history">
          Clear
        </button>
      </div>

      <div className="history-list">
        {history.map((entry) => (
          <div key={entry.id ?? entry.timestamp} className={`history-row ${entry.status}`}>
            <span className={`status-pill ${entry.status}`}>
              {entry.status === "passed" ? "✓ passed" : "✗ failed"}
            </span>
            <div className="history-ticket">{entry.ticket}</div>
            <div className="history-meta">
              {entry.filesChanged} file{entry.filesChanged !== 1 ? "s" : ""} changed
              <span className="dot-sep">·</span>
              {formatTimestamp(entry.timestamp)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTimestamp(ts) {
  // Backend sends a unix epoch (seconds); older client-only entries may
  // already be a formatted string — handle both gracefully.
  if (typeof ts === "number") {
    return new Date(ts * 1000).toLocaleString();
  }
  return ts;
}
