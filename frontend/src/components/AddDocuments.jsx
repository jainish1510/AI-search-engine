import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useAsync, useDebounce } from "../hooks.js";

const EMPTY = { title: "", url: "", tags: "", body: "" };

function SingleDocumentForm({ onIndexed }) {
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState(null);
  const text = useDebounce(`${form.title}\n${form.body}`.trim(), 500);
  const { data: preview } = useAsync((signal) => api.analyzeText(text, signal), [text], {
    enabled: text.length > 20,
  });

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setStatus({ kind: "pending", message: "Indexing…" });
    try {
      const doc = await api.createDocument({
        title: form.title,
        body: form.body,
        url: form.url || null,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setForm(EMPTY);
      setStatus({ kind: "ok", message: `Indexed “${doc.title}” with ${doc.keywords.length} keywords.` });
      onIndexed?.();
    } catch (err) {
      setStatus({ kind: "error", message: err.message });
    }
  };

  return (
    <form className="panel form" onSubmit={submit}>
      <h2 className="panel-title">Add a document</h2>
      <label>
        <span>
          Title <span className="required" aria-hidden="true">*</span>
        </span>
        <input required value={form.title} onChange={update("title")} maxLength={500} autoComplete="off" />
      </label>
      <label>
        <span>
          URL <span className="hint">(optional)</span>
        </span>
        <input type="url" inputMode="url" value={form.url} onChange={update("url")} placeholder="https://example.com/page" />
      </label>
      <label>
        <span>
          Tags <span className="hint">(comma separated)</span>
        </span>
        <input value={form.tags} onChange={update("tags")} placeholder="ai, search" autoComplete="off" />
      </label>
      <label>
        Content
        <textarea rows={8} value={form.body} onChange={update("body")} />
      </label>
      {preview?.keywords?.length > 0 && (
        <div className="keyword-preview" aria-live="polite">
          <span className="hint">Extracted keywords:</span>
          {preview.keywords.map((k) => (
            <span key={k.text} className="chip chip-keyword" title={`score ${k.score}`}>
              {k.text}
            </span>
          ))}
        </div>
      )}
      <button type="submit" className="primary" disabled={!form.title.trim() || status?.kind === "pending"}>
        {status?.kind === "pending" ? "Indexing…" : "Index document"}
      </button>
      <p className={`status status-${status?.kind || "ok"}`} role={status?.kind === "error" ? "alert" : "status"}>
        {status?.message}
      </p>
    </form>
  );
}

function BulkUpload({ onIndexed }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!job || job.status === "completed") return undefined;
    const id = setInterval(async () => {
      try {
        const next = await api.job(job.id);
        setJob(next);
        if (next.status === "completed") onIndexed?.();
      } catch (err) {
        setError(err.message);
      }
    }, 500);
    return () => clearInterval(id);
  }, [job, onIndexed]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    try {
      const parsed = JSON.parse(await file.text());
      const documents = Array.isArray(parsed) ? parsed : parsed.documents;
      if (!Array.isArray(documents)) throw new Error("Expected a JSON array of documents");
      const res = await api.bulkIndex(documents);
      setJob({ id: res.job_id, status: res.status, total: res.total, processed: 0, failed: 0 });
    } catch (err) {
      setError(err.message);
    }
  };

  const pct = job ? Math.round((job.processed / Math.max(job.total, 1)) * 100) : 0;
  return (
    <section className="panel form">
      <h2 className="panel-title">Bulk import</h2>
      <p className="hint">
        Upload a JSON array of <code>{"{ title, body, url?, tags? }"}</code> objects. Documents are indexed
        asynchronously in the background.
      </p>
      <label className="file">
        <input type="file" accept="application/json,.json" onChange={onFile} />
        <span className="button">Choose JSON file…</span>
      </label>
      {job && (
        <div className="job">
          <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${pct}%` }} />
          </div>
          <p className="hint" role="status" aria-live="polite">
            {job.status === "completed" ? "Done" : "Indexing"} — {job.processed}/{job.total} processed
            {job.failed > 0 && `, ${job.failed} failed`}
          </p>
        </div>
      )}
      {error && (
        <p className="status status-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

export default function AddDocuments({ onIndexed }) {
  return (
    <>
      <h1 className="page-title">Add documents</h1>
      <p className="page-intro">New documents are indexed immediately, with keywords extracted automatically.</p>
      <div className="two-column">
      <SingleDocumentForm onIndexed={onIndexed} />
      <BulkUpload onIndexed={onIndexed} />
      </div>
    </>
  );
}
