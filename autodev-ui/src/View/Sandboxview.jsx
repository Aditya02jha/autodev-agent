import { useState } from "react";
import FileList from "../components/FileList";
import DiffViewer from "../components/DiffViewer";
import BuildResult from "../components/BuildResult";

const API = "http://localhost:8000";

export default function SandboxView({ addToHistory }) {
  const [ticket, setTicket] = useState("");
  const [phase, setPhase] = useState("idle"); // idle | generating | review | applying | done
  const [sandboxId, setSandboxId] = useState(null);
  const [changes, setChanges] = useState([]);
  const [selected, setSelected] = useState(0);
  const [rejected, setRejected] = useState(new Set());
  const [buildResult, setBuildResult] = useState(null);
  const [error, setError] = useState("");

  // ── Generate ────────────────────────────────────────────────────────
  async function generate() {
    if (!ticket.trim()) return;
    setPhase("generating");
    setError("");
    setChanges([]);
    setSandboxId(null);
    setBuildResult(null);
    setRejected(new Set());

    try {
      const res = await fetch(`${API}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: ticket }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSandboxId(data.sandbox_id);
      setChanges(data.changes);
      setSelected(0);
      setPhase("review");
    } catch (e) {
      setError(e.message || "Generation failed");
      setPhase("idle");
    }
  }

  // ── Apply ────────────────────────────────────────────────────────────
  async function apply() {
    setPhase("applying");
    setError("");
    try {
      // Filter out any files the user rejected
      const approvedChanges = changes.filter((_, i) => !rejected.has(i));

      const res = await fetch(`${API}/apply/${sandboxId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved_indices: approvedChanges.map((_, i) => i),
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setBuildResult(data);
      setPhase("done");

      addToHistory({
        ticket,
        filesChanged: approvedChanges.length,
        status: Object.values(data.maven_results || {}).every(
          (r) => typeof r === "string" && r.includes("BUILD SUCCESS"),
        )
          ? "passed"
          : "failed",
        timestamp: new Date().toLocaleString(),
      });
    } catch (e) {
      setError(e.message || "Apply failed");
      setPhase("review");
    }
  }

  // ── Reject all ───────────────────────────────────────────────────────
  async function rejectAll() {
    if (sandboxId) {
      await fetch(`${API}/sandbox/${sandboxId}`, { method: "DELETE" }).catch(
        () => {},
      );
    }
    setPhase("idle");
    setChanges([]);
    setSandboxId(null);
    setBuildResult(null);
    setRejected(new Set());
  }

  function toggleReject(i) {
    setRejected((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  // ── Stats ─────────────────────────────────────────────────────────────
  const currentFile = changes[selected];
  const totalAdds = changes.reduce(
    (s, c) => s + countAdds(c.old_content, c.new_content),
    0,
  );
  const approvedCount = changes.length - rejected.size;

  return (
    <div className="sandbox-view">
      {/* ── Ticket input ── */}
      <div className="ticket-panel">
        <textarea
          className="ticket-textarea"
          rows={3}
          placeholder="Describe what to build or fix…  e.g. Add a GET /birthdays-today endpoint that returns employees born today"
          value={ticket}
          onChange={(e) => setTicket(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate();
          }}
          disabled={phase === "generating" || phase === "applying"}
        />
        <div className="ticket-actions">
          <button
            className="btn-primary"
            onClick={generate}
            disabled={
              !ticket.trim() || phase === "generating" || phase === "applying"
            }
          >
            {phase === "generating" ? "Generating…" : "Generate changes"}
          </button>
          {changes.length > 0 && (
            <button className="btn-ghost" onClick={rejectAll}>
              Clear sandbox
            </button>
          )}
          <span className="shortcut-hint">⌘ + Enter to generate</span>
        </div>
        {error && <div className="error-bar">{error}</div>}
      </div>

      {/* ── Sandbox bar ── */}
      {phase !== "idle" && changes.length > 0 && (
        <div className="sandbox-bar">
          <span className="sandbox-tag">⛶ Sandbox</span>
          <span className="sandbox-msg">
            Your files are untouched until you click Apply
          </span>
          <span className="stat-adds">+{totalAdds} lines</span>
          <span className="stat-files">
            {approvedCount} of {changes.length} files selected
          </span>
        </div>
      )}

      {/* ── Diff workspace ── */}
      {changes.length > 0 && (
        <div className="diff-workspace">
          <FileList
            changes={changes}
            selected={selected}
            onSelect={setSelected}
            rejected={rejected}
            onToggleReject={toggleReject}
          />

          <div className="diff-pane">
            {currentFile && (
              <>
                <div className="diff-topbar">
                  <span className="diff-filename">
                    {basename(currentFile.file_path)}
                  </span>
                  <span
                    className={`file-badge ${!currentFile.old_content ? "new" : "mod"}`}
                  >
                    {!currentFile.old_content ? "new file" : "modified"}
                  </span>
                  {rejected.has(selected) && (
                    <span className="file-badge rejected-badge">skipped</span>
                  )}
                  <span className="diff-explanation">
                    {currentFile.explanation}
                  </span>
                </div>
                <div className="diff-scroll">
                  <DiffViewer
                    oldContent={currentFile.old_content || ""}
                    newContent={currentFile.new_content || ""}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Footer actions ── */}
      {phase === "review" && changes.length > 0 && (
        <div className="sandbox-footer">
          <button className="btn-danger-ghost" onClick={rejectAll}>
            Reject all
          </button>
          <div style={{ flex: 1 }} />
          <button
            className="btn-primary"
            onClick={apply}
            disabled={approvedCount === 0}
          >
            Apply {approvedCount} file{approvedCount !== 1 ? "s" : ""} to disk →
          </button>
        </div>
      )}

      {phase === "applying" && (
        <div className="sandbox-footer">
          <span className="applying-msg">Writing files and running Maven…</span>
        </div>
      )}

      {/* ── Build result ── */}
      {buildResult && (
        <BuildResult
          result={buildResult}
          onDismiss={() => setBuildResult(null)}
        />
      )}
    </div>
  );
}

function basename(path) {
  return (path || "").replace(/\\/g, "/").split("/").pop();
}

function countAdds(oldContent, newContent) {
  const oldLines = oldContent ? oldContent.split("\n") : [];
  const newLines = newContent ? newContent.split("\n") : [];
  return Math.max(0, newLines.length - oldLines.length);
}
