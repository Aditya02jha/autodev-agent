import { AppProvider, useApp } from "./context/AppContext";
import Sidebar from "./components/Sidebar";
import SandboxView from "./View/Sandboxview";
import HistoryView from "./View/Historyview";
import AskView from "./View/Askview";
import SetupBanner from "./components/SetupBanner";
import { useLocalStorageState } from "./hooks/useLocalStorageState";

function Shell() {
  // Persisted so refreshing the page keeps you on the tab you were on.
  const [view, setView] = useLocalStorageState("autodev.view", "sandbox");
  const { indexed, setIndexed } = useApp();

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} indexed={indexed} />
      <div className="main-area">
        {!indexed && <SetupBanner onIndexed={() => setIndexed(true)} />}

        {/*
          Each view is kept mounted (just hidden) instead of being
          conditionally rendered. Previously `{view === "x" && <X/>}`
          unmounted the component the instant you switched tabs, which
          destroyed all of its local state — that was the root cause of
          "everything vanishes when I go to another tab". State itself now
          lives in AppContext (see context/AppContext.jsx), but keeping the
          views mounted also avoids re-running effects / refetching on every
          tab switch.
        */}
        <div style={{ display: view === "sandbox" ? "contents" : "none" }}>
          <SandboxView />
        </div>
        <div style={{ display: view === "history" ? "contents" : "none" }}>
          <HistoryView />
        </div>
        <div style={{ display: view === "ask" ? "contents" : "none" }}>
          <AskView />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
