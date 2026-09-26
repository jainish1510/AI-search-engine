import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAsync } from "../hooks.js";

/** Two-step delete: the first click asks for confirmation, which expires after a few seconds. */
function DeleteButton({ title, onConfirm }) {
  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!armed) return undefined;
    const id = setTimeout(() => setArmed(false), 4000);
    return () => clearTimeout(id);
  }, [armed]);

  const onClick = async () => {
    if (!armed) return setArmed(true);
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
      setArmed(false);
    }
  };
  return (
    <button
      type="button"
      className={`ghost danger ${armed ? "armed" : ""}`}
      onClick={onClick}
      onBlur={() => setArmed(false)}
      disabled={busy}
      aria-label={armed ? `Confirm deleting ${title}` : `Delete ${title}`}
    >
      {busy ? "Deleting…" : armed ? "Confirm delete" : "Delete"}
    </button>
  );
}

export default function IndexPage({ version, onChanged }) {
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const { data: stats } = useAsync(() => api.stats(), [version, refresh]);
  const { data: docs, error } = useAsync(() => api.listDocuments(page, 10), [page, version, refresh]);

  const [message, setMessage] = useState(null);

  const remove = async (doc) => {
    try {
      await api.deleteDocument(doc.id);
      setMessage({ kind: "ok", text: `Deleted “${doc.title}”.` });
      setRefresh((n) => n + 1);
      onChanged?.();
    } catch (err) {
      setMessage({ kind: "error", text: `Couldn’t delete “${doc.title}”: ${err.message}` });
    }
  };

  const pages = docs ? Math.ceil(docs.total / docs.size) : 1;
  return (
    <div className="index-page">
      <h1 className="page-title">Index</h1>
      <p className="page-intro">What’s in the search index, and what people are searching for.</p>
      {stats && (
        <div className="stat-tiles">
          <div className="stat">
            <span className="stat-value">{stats.documents.toLocaleString()}</span>
            <span className="stat-label">Documents</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.unique_terms.toLocaleString()}</span>
            <span className="stat-label">Unique terms</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.avg_body_length}</span>
            <span className="stat-label">Avg. terms / doc</span>
          </div>
        </div>
      )}
      <div className="two-column">
        <section className="panel">
          <h2 className="panel-title">Indexed documents</h2>
          {error && (
            <p className="status status-error" role="alert">
              Couldn’t load documents: {error.message}
            </p>
          )}
          <p className={`status status-${message?.kind || "ok"}`} role="status" aria-live="polite">
            {message?.text}
          </p>
          {docs && docs.total === 0 && (
            <p className="hint">No documents yet. Add some from the “Add documents” tab.</p>
          )}
          <ul className="doc-list">
            {docs?.items.map((doc) => (
              <li key={doc.id}>
                <div>
                  <strong>{doc.title}</strong>
                  <div className="doc-keywords">
                    {doc.keywords.slice(0, 4).map((k) => (
                      <span key={k.text} className="chip chip-keyword">
                        {k.text}
                      </span>
                    ))}
                  </div>
                </div>
                <DeleteButton title={doc.title} onConfirm={() => remove(doc)} />
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="pagination">
              <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page">
                ← Prev
              </button>
              <span className="hint" aria-live="polite">
                Page {page} of {pages}
              </span>
              <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)} aria-label="Next page">
                Next →
              </button>
            </div>
          )}
        </section>
        <div className="stack">
          {stats?.popular_queries?.length > 0 && (
            <section className="panel">
              <h2 className="panel-title">Popular searches</h2>
              <ol className="ranked">
                {stats.popular_queries.map((q) => (
                  <li key={q.query}>
                    <a href={`/?q=${encodeURIComponent(q.query)}`}>{q.query}</a>
                    <span className="facet-count">{q.count}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
          {stats && (
            <section className="panel">
              <h2 className="panel-title">Most frequent words</h2>
              <ol className="ranked">
                {stats.top_words.map((w) => (
                  <li key={w.word}>
                    <span>{w.word}</span>
                    <span className="facet-count">{w.freq}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
