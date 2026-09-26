import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAsync, useDebounce } from "../hooks.js";
import Facets from "./Facets.jsx";
import Logo from "./Logo.jsx";
import Pagination from "./Pagination.jsx";
import QueryInsights from "./QueryInsights.jsx";
import ResultCard from "./ResultCard.jsx";
import SearchBar from "./SearchBar.jsx";

const PAGE_SIZE = 10;
const EXAMPLES = [
  "how do search engines rank results?",
  '"neural networks" -recurrent',
  "car tag:energy",
  "machne lerning",
  "react vs node.js",
];

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  return {
    q: params.get("q") || "",
    page: Math.max(1, Number(params.get("page")) || 1),
    tags: params.getAll("tag"),
  };
}

function writeUrl({ q, page, tags }) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (page > 1) params.set("page", String(page));
  tags.forEach((t) => params.append("tag", t));
  const search = params.toString();
  const next = `${window.location.pathname}${search ? `?${search}` : ""}`;
  if (next !== `${window.location.pathname}${window.location.search}`) window.history.replaceState(null, "", next);
}

export default function SearchPage() {
  const [initial] = useState(readUrl);
  const [input, setInput] = useState(initial.q);
  const [page, setPage] = useState(initial.page);
  const [tags, setTags] = useState(initial.tags);
  // Results update as the user types (debounced); Enter or picking a suggestion runs immediately.
  const debounced = useDebounce(input, 300);
  const [forced, setForced] = useState(null);
  const query = forced ?? debounced;

  const previousQuery = useRef(query);
  useEffect(() => {
    if (previousQuery.current !== query) setPage(1);
    previousQuery.current = query;
  }, [query]);
  useEffect(() => writeUrl({ q: query.trim(), page, tags }), [query, page, tags]);

  const active = query.trim().length > 0 || tags.length > 0;
  const [attempt, setAttempt] = useState(0);
  const { data, error, loading } = useAsync(
    (signal) => api.search(query, { page, size: PAGE_SIZE, tags }, signal),
    [query, page, tags.join("|"), attempt],
    { enabled: active },
  );

  useEffect(() => {
    document.title = query.trim() ? `${query.trim()} · Lumen Search` : "Lumen Search";
  }, [query]);

  const toggleTag = (tag) => {
    setTags((current) => (current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag]));
    setPage(1);
  };
  const clearTags = () => {
    setTags([]);
    setPage(1);
  };
  const typeQuery = (text) => {
    setInput(text);
    setForced(null);
  };
  const runQuery = (text) => {
    setInput(text);
    setForced(text);
  };
  const changePage = (n) => {
    setPage(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const status = error
    ? "Search failed"
    : data
      ? `${data.total.toLocaleString()} result${data.total === 1 ? "" : "s"} in ${data.took_ms} ms`
      : "";

  return (
    <div className={`search-page ${active ? "has-query" : "is-home"}`}>
      {!active && (
        <div className="hero">
          <Logo size={64} />
          <h1>
            Search with <span className="accent">understanding</span>
          </h1>
          <p>Ask in plain language. Results update as you type, ranked by relevance.</p>
        </div>
      )}
      <SearchBar value={input} onChange={typeQuery} onSubmit={runQuery} autoFocus />

      {!active && (
        <div className="examples">
          <span id="examples-label">Try:</span>
          <ul aria-labelledby="examples-label">
            {EXAMPLES.map((ex) => (
              <li key={ex}>
                <button type="button" className="chip chip-example" onClick={() => runQuery(ex)}>
                  {ex}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {active && (
        <div className="search-layout">
          <h1 className="visually-hidden">Search results for “{query.trim() || tags.map((t) => `#${t}`).join(" ")}”</h1>
          <div className="results-column" aria-busy={loading}>
            <div className="results-status">
              {loading && <span className="spinner" aria-hidden="true" />}
              <span role="status" aria-live="polite">
                {loading && !data ? "Searching…" : status}
              </span>
            </div>

            {tags.length > 0 && (
              <div className="active-filters" aria-label="Active filters">
                {tags.map((tag) => (
                  <button key={tag} type="button" className="chip chip-tag chip-removable" onClick={() => toggleTag(tag)}>
                    #{tag}
                    <span aria-hidden="true"> ×</span>
                    <span className="visually-hidden"> (remove filter)</span>
                  </button>
                ))}
                <button type="button" className="link-button" onClick={clearTags}>
                  Clear all
                </button>
              </div>
            )}

            {data?.did_you_mean && (
              <p className="did-you-mean">
                Did you mean{" "}
                <button type="button" className="link" onClick={() => runQuery(data.did_you_mean)}>
                  {data.did_you_mean}
                </button>
                ?
              </p>
            )}

            {error && (
              <div className="error" role="alert">
                <span>Couldn’t reach the search service: {error.message}</span>
                <button type="button" className="ghost" onClick={() => setAttempt((n) => n + 1)}>
                  Try again
                </button>
              </div>
            )}

            {data && !error && data.total === 0 && (
              <div className="empty">
                <h3>No matching documents</h3>
                <p>Try fewer or different words, remove quotes and exclusions, or check the spelling.</p>
                {tags.length > 0 && (
                  <button type="button" className="ghost" onClick={clearTags}>
                    Search without tag filters
                  </button>
                )}
              </div>
            )}

            {loading && !data && !error && <ResultSkeleton />}

            <div className={`results ${loading && data ? "is-stale" : ""}`}>
              {data?.results.map((r) => (
                <ResultCard key={r.id} result={r} onTagClick={toggleTag} />
              ))}
            </div>
            {data && <Pagination page={data.page} pages={data.pages} onChange={changePage} />}
          </div>

          <aside className="sidebar" aria-label="Search tools">
            {data && <Facets facets={data.facets} selected={tags} onToggle={toggleTag} />}
            {data && <QueryInsights analysis={data.analysis} />}
            <section className="panel syntax">
              <h2 className="panel-title">Search tips</h2>
              <ul>
                <li><code>"exact phrase"</code> match words in order</li>
                <li><code>-word</code> exclude documents containing a word</li>
                <li><code>tag:name</code> only documents with a tag</li>
                <li><code>title:word</code> word must appear in the title</li>
                <li>Press <kbd>/</kbd> anywhere to jump to the search box</li>
              </ul>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}

function ResultSkeleton() {
  return (
    <div className="results" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="result skeleton">
          <div className="sk sk-line sk-short" />
          <div className="sk sk-title" />
          <div className="sk sk-line" />
          <div className="sk sk-line sk-mid" />
        </div>
      ))}
    </div>
  );
}
