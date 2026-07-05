import { useState } from "react";

const API = "http://localhost:8000";

export default function AskView() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    setAnswer("");
    setError("");
    try {
      const res = await fetch(`${API}/ask?q=${encodeURIComponent(q)}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setAnswer(data.answer);
    } catch (e) {
      setError(e.message || "Failed to get answer");
    } finally {
      setLoading(false);
    }
  }

  const SUGGESTIONS = [
    "What REST endpoints exist?",
    "Where is Redis used?",
    "What does EmployeeService do?",
    "List all database entities",
  ];

  return (
    <div className="ask-view">
      <div className="view-header">
        <h2>Ask codebase</h2>
      </div>

      <div className="ask-input-row">
        <input
          className="ask-input"
          placeholder="What controllers exist? Where is Redis used?"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button
          className="btn-primary"
          onClick={ask}
          disabled={!q.trim() || loading}
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </div>

      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="suggestion-chip"
            onClick={() => {
              setQ(s);
            }}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <div className="error-bar">{error}</div>}
      {answer && (
        <div className="ask-answer">
          <div className="answer-label">Answer</div>
          <div className="answer-body">{answer}</div>
        </div>
      )}
    </div>
  );
}
