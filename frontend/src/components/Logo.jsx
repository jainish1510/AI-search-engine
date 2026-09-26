import { useId } from "react";

/** Brand mark: a magnifier with an "AI" spark. Decorative unless a title is given. */
export default function Logo({ size = 28, title }) {
  const gradientId = `logo-gradient-${useId().replace(/:/g, "")}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className="logo"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5c7cfa" />
          <stop offset="1" stopColor="#3b5bdb" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill={`url(#${gradientId})`} />
      <circle cx="14" cy="14" r="6.5" fill="none" stroke="#fff" strokeWidth="2.6" />
      <path d="M19 19l5.5 5.5" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" />
      <path d="M24 5.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z" fill="#ffd43b" />
    </svg>
  );
}
