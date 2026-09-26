const INTENT_LABELS = {
  question: "Question",
  comparison: "Comparison",
  transactional: "Transactional",
  navigational: "Navigational",
  informational: "Informational",
};

function Row({ label, items, render = (x) => x, className = "" }) {
  if (!items?.length) return null;
  return (
    <div className="insight-row">
      <dt>{label}</dt>
      <dd>
        {items.map((item) => (
          <span key={typeof item === "string" ? item : JSON.stringify(item)} className={`chip ${className}`}>
            {render(item)}
          </span>
        ))}
      </dd>
    </div>
  );
}

/** Shows how the NLP pipeline interpreted the query. */
export default function QueryInsights({ analysis }) {
  if (!analysis) return null;
  const expansions = Object.entries(analysis.expansions || {}).map(([term, syns]) => `${term} → ${syns.join(", ")}`);
  return (
    <section className="panel" aria-label="Query understanding">
      <h2 className="panel-title">Query understanding</h2>
      <dl className="insights">
        <div className="insight-row">
          <dt>Intent</dt>
          <dd>
            <span className={`intent intent-${analysis.intent}`}>{INTENT_LABELS[analysis.intent] || analysis.intent}</span>
          </dd>
        </div>
        <Row label="Keywords" items={analysis.keywords} className="chip-keyword" />
        <Row label="Index terms" items={analysis.terms} className="chip-mono" />
        <Row label="Phrases" items={analysis.phrases} render={(p) => `“${p}”`} />
        <Row label="Excluded" items={analysis.excluded} className="chip-excluded" render={(t) => `−${t}`} />
        <Row label="Tags" items={analysis.tags} className="chip-tag" render={(t) => `#${t}`} />
        <Row label="Synonyms" items={expansions} className="chip-mono" />
      </dl>
    </section>
  );
}
