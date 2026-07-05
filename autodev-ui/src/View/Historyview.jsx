export default function HistoryView({ history }) {
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
      </div>

      <div className="history-list">
        {history.map((entry, i) => (
          <div key={i} className={`history-row ${entry.status}`}>
            <span className={`status-pill ${entry.status}`}>
              {entry.status === "passed" ? "✓ passed" : "✗ failed"}
            </span>
            <div className="history-ticket">{entry.ticket}</div>
            <div className="history-meta">
              {entry.filesChanged} file{entry.filesChanged !== 1 ? "s" : ""}{" "}
              changed
              <span className="dot-sep">·</span>
              {entry.timestamp}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
