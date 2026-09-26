import Highlight from "./Highlight.jsx";

export default function ResultCard({ result, onTagClick }) {
  const pct = Math.round(result.relevance * 100);
  return (
    <article className="result">
      <div className="result-head">
        {result.url && (
          <a className="result-url" href={result.url} target="_blank" rel="noreferrer noopener" tabIndex={-1} aria-hidden="true">
            {result.url.replace(/^https?:\/\//, "")}
          </a>
        )}
        <span className="relevance" role="img" aria-label={`Relevance ${pct}%`} title={`Relevance ${pct}% (BM25F score ${result.score})`}>
          <span className="relevance-bar" style={{ width: `${pct}%` }} />
          <span className="relevance-label" aria-hidden="true">{pct}%</span>
        </span>
      </div>
      <h2 className="result-title">
        {result.url ? (
          <a href={result.url} target="_blank" rel="noreferrer noopener">
            <Highlight segments={result.title_segments} fallback={result.title} />
            <span className="visually-hidden"> (opens in a new tab)</span>
          </a>
        ) : (
          <Highlight segments={result.title_segments} fallback={result.title} />
        )}
      </h2>
      <p className="result-snippet">
        <Highlight segments={result.snippet} />
      </p>
      <div className="result-meta">
        {result.tags.map((tag) => (
          <button
            key={tag}
            type="button"
            className="chip chip-tag"
            onClick={() => onTagClick?.(tag)}
            title={`Filter by #${tag}`}
            aria-label={`Filter by tag ${tag}`}
          >
            #{tag}
          </button>
        ))}
        {result.keywords.map((kw) => (
          <span key={kw} className="chip chip-keyword">
            {kw}
          </span>
        ))}
      </div>
    </article>
  );
}
