import { useCallback, useEffect, useState } from "react";
import AddDocuments from "./components/AddDocuments.jsx";
import IndexPage from "./components/IndexPage.jsx";
import Logo from "./components/Logo.jsx";
import SearchPage from "./components/SearchPage.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";

const TABS = [
  { id: "search", label: "Search", title: "Search" },
  { id: "add", label: "Add documents", short: "Add", title: "Add documents" },
  { id: "index", label: "Index", title: "Index statistics" },
];

const tabFromHash = () => {
  const id = window.location.hash.replace("#", "");
  return TABS.some((t) => t.id === id) ? id : "search";
};

export default function App() {
  const [tab, setTabState] = useState(tabFromHash);
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  // Keep the active section in the URL hash so back/forward and reload restore it.
  useEffect(() => {
    const onHash = () => setTabState(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const setTab = (id) => {
    if (id === tab) return;
    const url = id === "search" ? `${window.location.pathname}${window.location.search}` : `#${id}`;
    window.history.pushState(null, "", url);
    setTabState(id);
    document.getElementById("main")?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    if (tab !== "search") document.title = `${TABS.find((t) => t.id === tab).title} · Lumen Search`;
  }, [tab]);

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <button type="button" className="brand" onClick={() => setTab("search")} aria-label="Lumen Search home">
          <Logo size={30} />
          <span className="brand-name">Lumen</span>
        </button>
        <nav className="tabs" aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "active" : ""}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
              aria-label={t.short ? t.label : undefined}
            >
              {t.short ? (
                <>
                  <span className="label-long">{t.label}</span>
                  <span className="label-short" aria-hidden="true">
                    {t.short}
                  </span>
                </>
              ) : (
                t.label
              )}
            </button>
          ))}
        </nav>
        <div className="topbar-actions">
          <ThemeToggle />
        </div>
      </header>
      <main id="main" className="container" tabIndex={-1}>
        {tab === "search" && <SearchPage key={version} />}
        {tab === "add" && <AddDocuments onIndexed={bump} />}
        {tab === "index" && <IndexPage version={version} onChanged={bump} />}
      </main>
    </div>
  );
}
