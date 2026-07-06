import FileList from "../components/FileList";
import DiffViewer from "../components/DiffViewer";
import BuildResult from "../components/BuildResult";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";

export default function SandboxView() {
  const { sandbox, updateSandbox, resetSandbox, toggleRejected, addHistoryEntry, rehydrating } =
    useApp();
  const {
    ticket,
    phase,
    sandboxId,
    changes,
    selected,
    rejected: rejectedArr,
    buildResult,
    error,
  } = sandbox;
  const rejected = new Set(rejectedArr);

  // ── Generate ────────────────────────────────────────────────────────
  async function generate() {
    if (!ticket.trim()) return;
    updateSandbox({
      phase: "generating",
      error: "",
      changes: [],
      sandboxId: null,
      buildResult: null,
      rejected: [],
    });

    try {
      const data = await api.post("/generate", { task: ticket });
      updateSandbox({
        sandboxId: data.sandbox_id,
        changes: data.changes,
        planSummary: data.plan_summary || "",
        selected: 0,
        phase: "review",
      });
    } catch (e) {
      updateSandbox({ error: e.message || "Generation failed", phase: "idle" });
    }
  }

  // ── Apply ────────────────────────────────────────────────────────────
  async function apply() {
    updateSandbox({ phase: "applying", error: "" });
    try {
      // Filter out any files the user rejected
      const approvedIndices = changes.map((_, i) => i).filter((i) => !rejected.has(i));

      const data = await api.post(`/apply/${sandboxId}`, {
        approved_indices: approvedIndices,
      });
      updateSandbox({ buildResult: data, phase: "done" });

      // Backend now persists this run permanently and hands back the
      // canonical entry (id, timestamp, etc.) — use that instead of
      // fabricating a client-side-only record that vanishes on refresh.
      if (data.history_entry) {
        addHistoryEntry(data.history_entry);
      }
    } catch (e) {
      updateSandbox({ error: e.message || "Apply failed", phase: "review" });
    }
  }

  // ── Reject all ───────────────────────────────────────────────────────
  async function rejectAll() {
    if (sandboxId) {
      await api.del(`/sandbox/${sandboxId}`).catch(() => {});
    }
    resetSandbox();
  }

  function setSelected(i) {
    updateSandbox({ selected: i });
  }

  // ── Stats ─────────────────────────────────────────────────────────────
  const currentFile = changes[selected];
  const totalAdds = changes.reduce((s, c) => s + countAdds(c.old_content, c.new_content), 0);
  const approvedCount = changes.length - rejected.size;

  if (rehydrating) {
    return (
      <div className="sandbox-view">
        <div className="empty-state">
          <div className="empty-title">Restoring your session…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="sandbox-view">
      {/* ── Ticket input ── */}
      <div className="ticket-panel">
        <textarea
          className="ticket-textarea"
          rows={3}
          placeholder="Describe what to build or fix…  e.g. Add a GET /birthdays-today endpoint that returns employees born today"
          value={ticket}
          onChange={(e) => updateSandbox({ ticket: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate();
          }}
          disabled={phase === "generating" || phase === "applying"}
        />
        <div className="ticket-actions">
          <button
            className="btn-primary"
            onClick={generate}
            disabled={!ticket.trim() || phase === "generating" || phase === "applying"}
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
          <span className="sandbox-msg">Your files are untouched until you click Apply</span>
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
            onToggleReject={toggleRejected}
          />

          <div className="diff-pane">
            {currentFile && (
              <>
                <div className="diff-topbar">
                  <span className="diff-filename">{basename(currentFile.file_path)}</span>
                  <span className={`file-badge ${!currentFile.old_content ? "new" : "mod"}`}>
                    {!currentFile.old_content ? "new file" : "modified"}
                  </span>
                  {rejected.has(selected) && (
                    <span className="file-badge rejected-badge">skipped</span>
                  )}
                  <span className="diff-explanation">{currentFile.explanation}</span>
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
          <button className="btn-primary" onClick={apply} disabled={approvedCount === 0}>
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
        <BuildResult result={buildResult} onDismiss={() => updateSandbox({ buildResult: null })} />
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
