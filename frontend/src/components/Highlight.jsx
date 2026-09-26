/** Renders server-provided highlight segments safely (no innerHTML). */
export default function Highlight({ segments, fallback = "" }) {
  if (!segments?.length) return fallback;
  return segments.map((seg, i) => (seg.highlight ? <mark key={i}>{seg.text}</mark> : <span key={i}>{seg.text}</span>));
}
