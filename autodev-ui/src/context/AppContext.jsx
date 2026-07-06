import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { useLocalStorageState } from "../hooks/useLocalStorageState";

const AppContext = createContext(null);

const EMPTY_SANDBOX = {
  ticket: "",
  phase: "idle", // idle | generating | review | applying | done
  sandboxId: null,
  planSummary: "",
  changes: [],
  selected: 0,
  rejected: [], // array (not Set) so it's JSON-serializable for localStorage
  buildResult: null,
  error: "",
};

/**
 * AppProvider is mounted once, above the view router in App.jsx, so its
 * state survives switching between Sandbox / History / Ask tabs (previously
 * each view's local useState was destroyed on unmount whenever the tab
 * changed). It also mirrors the important bits to localStorage so a full
 * page refresh doesn't lose an in-progress review either, and reconciles
 * with the backend (which is now the durable source of truth) on load.
 */
export function AppProvider({ children }) {
  const [indexed, setIndexed] = useLocalStorageState("autodev.indexed", false);
  const [sandbox, setSandbox] = useLocalStorageState("autodev.sandbox", EMPTY_SANDBOX);
  const [ask, setAsk] = useLocalStorageState("autodev.ask", { q: "", answer: "" });
  const [history, setHistory] = useLocalStorageState("autodev.history", []);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [rehydrating, setRehydrating] = useState(true);

  // ── Rehydrate sandbox from the backend on first load ──────────────────
  // localStorage told us we *had* a sandboxId, but the backend (sqlite) is
  // the source of truth — the server may have restarted, the sandbox may
  // have expired (TTL cleanup), or it may already have been applied from
  // another tab. Confirm before trusting stale local state.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (sandbox.sandboxId && sandbox.phase === "review") {
        try {
          const fresh = await api.get(`/sandbox/${sandbox.sandboxId}`);
          if (cancelled) return;
          setSandbox((s) => ({
            ...s,
            changes: fresh.changes,
            planSummary: fresh.plan_summary || s.planSummary,
          }));
        } catch {
          if (cancelled) return;
          // Sandbox is gone server-side — don't leave the UI stuck showing
          // a review screen for changes that no longer exist anywhere.
          setSandbox(EMPTY_SANDBOX);
        }
      }
      if (!cancelled) setRehydrating(false);
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Load history from the backend (durable) and merge into local cache ──
  const refreshHistory = useCallback(async () => {
    try {
      const data = await api.get("/history");
      setHistory(data.history || []);
    } catch {
      // Backend unreachable — keep whatever we had cached locally instead
      // of wiping the list the user can already see.
    } finally {
      setHistoryLoaded(true);
    }
  }, [setHistory]);

  useEffect(() => {
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateSandbox = useCallback(
    (patch) => setSandbox((s) => ({ ...s, ...(typeof patch === "function" ? patch(s) : patch) })),
    [setSandbox],
  );

  const resetSandbox = useCallback(() => setSandbox(EMPTY_SANDBOX), [setSandbox]);

  const toggleRejected = useCallback(
    (i) =>
      setSandbox((s) => {
        const set = new Set(s.rejected);
        set.has(i) ? set.delete(i) : set.add(i);
        return { ...s, rejected: Array.from(set) };
      }),
    [setSandbox],
  );

  const addHistoryEntry = useCallback(
    (entry) => setHistory((h) => [entry, ...h]),
    [setHistory],
  );

  const clearHistory = useCallback(async () => {
    setHistory([]);
    try {
      await api.del("/history");
    } catch {
      // best-effort — local list is already cleared for responsiveness
    }
  }, [setHistory]);

  const value = useMemo(
    () => ({
      indexed,
      setIndexed,
      sandbox,
      setSandbox,
      updateSandbox,
      resetSandbox,
      toggleRejected,
      ask,
      setAsk,
      history,
      historyLoaded,
      refreshHistory,
      addHistoryEntry,
      clearHistory,
      rehydrating,
    }),
    [indexed, sandbox, ask, history, historyLoaded, rehydrating, setIndexed, setSandbox, updateSandbox, resetSandbox, toggleRejected, setAsk, refreshHistory, addHistoryEntry, clearHistory],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- context + its hook are intentionally co-located
export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within an AppProvider");
  return ctx;
}
