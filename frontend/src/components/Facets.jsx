export default function Facets({ facets, selected, onToggle }) {
  const known = new Set(facets.map((f) => f.tag));
  const items = [...facets, ...selected.filter((t) => !known.has(t)).map((tag) => ({ tag, count: 0 }))];
  if (!items.length) return null;
  return (
    <section className="panel" aria-label="Filter by tag">
      <h2 className="panel-title">Refine by tag</h2>
      <ul className="facets">
        {items.map(({ tag, count }) => (
          <li key={tag}>
            <label>
              <input type="checkbox" checked={selected.includes(tag)} onChange={() => onToggle(tag)} />
              <span className="facet-name">{tag}</span>
              <span className="facet-count">{count}</span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
