import Highlight from "./Highlight.jsx";

export default function ResultCard({ result, onTagClick }) {
  const pct = Math.round(result.relevance * 100);
  return (
    <article className="result">
      <div className="result-head">
        {result.url && (
          <a className="result-url" href={result.url} target="_blank" rel="noreferrer noopener">
            {result.url.replace(/^https?:\/\//, "")}
          </a>
        )}
        <span className="relevance" title={`BM25F score ${result.score}`}>
          <span className="relevance-bar" style={{ width: `${pct}%` }} />
          <span className="relevance-label">{pct}%</span>
        </span>
      </div>
      <h3 className="result-title">
        {result.url ? (
          <a href={result.url} target="_blank" rel="noreferrer noopener">
            <Highlight segments={result.title_segments} fallback={result.title} />
          </a>
        ) : (
          <Highlight segments={result.title_segments} fallback={result.title} />
        )}
      </h3>
      <p className="result-snippet">
        <Highlight segments={result.snippet} />
      </p>
      <div className="result-meta">
        {result.tags.map((tag) => (
          <button key={tag} type="button" className="chip chip-tag" onClick={() => onTagClick?.(tag)}>
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
