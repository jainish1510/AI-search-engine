import { useState } from "react";
import { api } from "../api/client.js";
import { useAsync } from "../hooks.js";

export default function IndexPage({ version, onChanged }) {
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const { data: stats } = useAsync(() => api.stats(), [version, refresh]);
  const { data: docs, error } = useAsync(() => api.listDocuments(page, 10), [page, version, refresh]);

  const remove = async (id) => {
    await api.deleteDocument(id);
    setRefresh((n) => n + 1);
    onChanged?.();
  };

  const pages = docs ? Math.ceil(docs.total / docs.size) : 1;
  return (
    <div className="index-page">
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
          {error && <p className="status status-error">{error.message}</p>}
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
                <button type="button" className="ghost danger" onClick={() => remove(doc.id)} aria-label={`Delete ${doc.title}`}>
                  Delete
                </button>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="pagination">
              <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                ← Prev
              </button>
              <span className="hint">
                {page} / {pages}
              </span>
              <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)}>
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
