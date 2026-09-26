import { useCallback, useState } from "react";
import AddDocuments from "./components/AddDocuments.jsx";
import IndexPage from "./components/IndexPage.jsx";
import SearchPage from "./components/SearchPage.jsx";

const TABS = [
  { id: "search", label: "Search" },
  { id: "add", label: "Add documents" },
  { id: "index", label: "Index" },
];

export default function App() {
  const [tab, setTab] = useState("search");
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  return (
    <div className="app">
      <header className="topbar">
        <button type="button" className="brand" onClick={() => setTab("search")}>
          <span className="brand-mark" aria-hidden="true" />
          Lumen
        </button>
        <nav className="tabs" aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "active" : ""}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="container">
        {tab === "search" && <SearchPage key={version} />}
        {tab === "add" && <AddDocuments onIndexed={bump} />}
        {tab === "index" && <IndexPage version={version} onChanged={bump} />}
      </main>
    </div>
  );
}
