import { useState } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";

const SUGGESTIONS = [
  "What REST endpoints exist?",
  "Where is Redis used?",
  "What does EmployeeService do?",
  "List all database entities",
];

export default function AskView() {
  const { ask, setAsk } = useApp();
  const { q, answer } = ask;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function askQuestion() {
    if (!q.trim()) return;
    setLoading(true);
    setAsk((a) => ({ ...a, answer: "" }));
    setError("");
    try {
      const data = await api.get(`/ask?q=${encodeURIComponent(q)}`);
      setAsk((a) => ({ ...a, answer: data.answer }));
    } catch (e) {
      setError(e.message || "Failed to get answer");
    } finally {
      setLoading(false);
    }
  }

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
          onChange={(e) => setAsk((a) => ({ ...a, q: e.target.value }))}
          onKeyDown={(e) => e.key === "Enter" && askQuestion()}
        />
        <button className="btn-primary" onClick={askQuestion} disabled={!q.trim() || loading}>
          {loading ? "Asking…" : "Ask"}
        </button>
      </div>

      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="suggestion-chip"
            onClick={() => setAsk((a) => ({ ...a, q: s }))}
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
