export default function Pagination({ page, pages, onChange }) {
  if (pages <= 1) return null;
  const start = Math.max(1, Math.min(page - 2, pages - 4));
  const numbers = Array.from({ length: Math.min(5, pages) }, (_, i) => start + i);
  return (
    <nav className="pagination" aria-label="Pagination">
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page">
        ← Prev
      </button>
      {numbers.map((n) => (
        <button
          type="button"
          key={n}
          className={n === page ? "current" : ""}
          aria-current={n === page ? "page" : undefined}
          aria-label={`Page ${n}`}
          onClick={() => onChange(n)}
        >
          {n}
        </button>
      ))}
      <button type="button" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page">
        Next →
      </button>
    </nav>
  );
}
