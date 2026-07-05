import { useState } from "react";
import Sidebar from "./components/Sidebar";
import SandboxView from "./View/Sandboxview";
import HistoryView from "./View/Historyview";
import AskView from "./View/Askview";
import SetupBanner from "./components/SetupBanner";

export default function App() {
  const [view, setView] = useState("sandbox");
  const [history, setHistory] = useState([]);
  const [indexed, setIndexed] = useState(false);

  function addToHistory(entry) {
    setHistory((h) => [entry, ...h]);
  }

  return (
    <div className="app-shell">
      <Sidebar view={view} setView={setView} indexed={indexed} />
      <div className="main-area">
        {!indexed && <SetupBanner onIndexed={() => setIndexed(true)} />}
        {view === "sandbox" && <SandboxView addToHistory={addToHistory} />}
        {view === "history" && <HistoryView history={history} />}
        {view === "ask" && <AskView />}
      </div>
    </div>
  );
}
