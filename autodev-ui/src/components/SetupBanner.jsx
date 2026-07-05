import { useState } from "react";

export default function SetupBanner({ onIndexed }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function index() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/index", {
        method: "POST",
      });
      if (!res.ok) throw new Error(await res.text());
      onIndexed();
    } catch (e) {
      setError(
        e.message || "Could not reach server. Is uvicorn running on :8000?",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="setup-banner">
      <div className="setup-inner">
        <span className="setup-icon">⚠</span>
        <div>
          <strong>Codebase not indexed yet.</strong> Index once so the agent can
          understand your project.
          {error && <div className="setup-error">{error}</div>}
        </div>
        <button
          className="btn-primary small"
          onClick={index}
          disabled={loading}
        >
          {loading ? "Indexing…" : "Index now"}
        </button>
      </div>
    </div>
  );
}
