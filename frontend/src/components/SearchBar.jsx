import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client.js";
import { useAsync, useDebounce } from "../hooks.js";

/** Search input with debounced autocomplete suggestions and keyboard navigation. */
export default function SearchBar({ value, onChange, onSubmit, autoFocus = false }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const inputRef = useRef(null);
  const debounced = useDebounce(value, 150);
  const { data } = useAsync((signal) => api.suggest(debounced, signal), [debounced], {
    enabled: open && debounced.trim().length > 0,
  });
  const suggestions = (data?.suggestions || []).filter((s) => s !== value.trim().toLowerCase());

  useEffect(() => setActive(-1), [data]);

  // "/" focuses the search box from anywhere (unless the user is typing elsewhere).
  useEffect(() => {
    const onKey = (event) => {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      const el = document.activeElement;
      if (el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))) return;
      event.preventDefault();
      inputRef.current?.focus();
      inputRef.current?.select();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const choose = (text) => {
    onChange(text);
    onSubmit?.(text);
    setOpen(false);
  };

  const onKeyDown = (event) => {
    if (event.key === "ArrowDown" && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % suggestions.length);
    } else if (event.key === "ArrowUp" && suggestions.length) {
      event.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (open && active >= 0 && suggestions[active]) choose(suggestions[active]);
      else {
        onSubmit?.(value);
        setOpen(false);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  const showList = open && suggestions.length > 0;
  return (
    <div className="searchbar">
      <form role="search" onSubmit={(e) => e.preventDefault()}>
        <svg className="searchbar-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M20 20l-4.3-4.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          type="search"
          aria-label="Search"
          aria-autocomplete="list"
          enterKeyHint="search"
          placeholder="Ask a question or type keywords…"
          value={value}
          autoFocus={autoFocus}
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onKeyDown={onKeyDown}
        />
        {!value && (
          <kbd className="searchbar-kbd" aria-hidden="true" title="Press / to search">
            /
          </kbd>
        )}
        {value && (
          <button
            type="button"
            className="searchbar-clear"
            aria-label="Clear search"
            onClick={() => {
              onChange("");
              inputRef.current?.focus();
            }}
          >
            ×
          </button>
        )}
      </form>
      {showList && (
        <ul className="suggestions" id={listId} role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={s}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(s);
              }}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
