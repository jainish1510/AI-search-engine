import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAsync, useDebounce } from "../hooks.js";
import Facets from "./Facets.jsx";
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
  const { data, error, loading } = useAsync(
    (signal) => api.search(query, { page, size: PAGE_SIZE, tags }, signal),
    [query, page, tags.join("|")],
    { enabled: active },
  );

  const toggleTag = (tag) => {
    setTags((current) => (current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag]));
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

  return (
    <div className={`search-page ${active ? "has-query" : "is-home"}`}>
      {!active && (
        <div className="hero">
          <h1>
            Search with <span className="accent">understanding</span>
          </h1>
          <p>Natural-language queries, keyword extraction and BM25F relevance ranking over your documents.</p>
        </div>
      )}
      <SearchBar value={input} onChange={typeQuery} onSubmit={runQuery} autoFocus />

      {!active && (
        <div className="examples">
          <span>Try:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" className="chip chip-example" onClick={() => runQuery(ex)}>
              {ex}
            </button>
          ))}
        </div>
      )}

      {active && (
        <div className="search-layout">
          <div className="results-column" aria-live="polite" aria-busy={loading}>
            <div className="results-status">
              {loading && <span className="spinner" aria-label="Searching" />}
              {data && !error && (
                <span>
                  {data.total.toLocaleString()} result{data.total === 1 ? "" : "s"} in {data.took_ms} ms
                </span>
              )}
            </div>

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
                Search failed: {error.message}
              </div>
            )}

            {data && !error && data.total === 0 && (
              <div className="empty">
                <h3>No matching documents</h3>
                <p>Try fewer words, remove quotes or exclusions, or check the spelling.</p>
              </div>
            )}

            <div className={`results ${loading ? "is-stale" : ""}`}>
              {data?.results.map((r) => (
                <ResultCard key={r.id} result={r} onTagClick={toggleTag} />
              ))}
            </div>
            {data && <Pagination page={data.page} pages={data.pages} onChange={changePage} />}
          </div>

          <aside className="sidebar">
            {data && <Facets facets={data.facets} selected={tags} onToggle={toggleTag} />}
            {data && <QueryInsights analysis={data.analysis} />}
            <section className="panel syntax">
              <h2 className="panel-title">Search syntax</h2>
              <ul>
                <li><code>"exact phrase"</code> match words in order</li>
                <li><code>-word</code> exclude documents containing a word</li>
                <li><code>tag:name</code> only documents with a tag</li>
                <li><code>title:word</code> word must appear in the title</li>
              </ul>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}
