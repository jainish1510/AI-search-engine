import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import Highlight from "./components/Highlight.jsx";

const searchResponse = {
  query: "neural",
  total: 1,
  page: 1,
  size: 10,
  pages: 1,
  took_ms: 3.2,
  did_you_mean: null,
  facets: [{ tag: "ai", count: 1 }],
  analysis: { raw: "neural", terms: ["neural"], keywords: ["neural"], phrases: [], excluded: [], tags: [], title_terms: [], expansions: {}, intent: "informational", is_question: false },
  results: [
    {
      id: "1",
      title: "Deep Learning and Neural Networks",
      title_segments: [{ text: "Deep Learning and ", highlight: false }, { text: "Neural", highlight: true }, { text: " Networks", highlight: false }],
      url: "https://example.com/dl",
      tags: ["ai"],
      keywords: ["neural networks"],
      snippet: [{ text: "Deep learning uses ", highlight: false }, { text: "neural", highlight: true }, { text: " networks.", highlight: false }],
      score: 4.2,
      relevance: 1,
      matched_terms: ["neural"],
    },
  ],
};

function mockFetch() {
  return vi.fn(async (url) => {
    const { pathname } = new URL(url);
    const body = pathname === "/api/search" ? searchResponse : pathname === "/api/suggest" ? { suggestions: ["neural networks"] } : {};
    return { ok: true, status: 200, json: async () => body };
  });
}

describe("App", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
    global.fetch = mockFetch();
  });
  afterEach(() => vi.restoreAllMocks());

  it("shows the home screen with example queries", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /search with understanding/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: '"neural networks" -recurrent' })).toBeInTheDocument();
  });

  it("searches as the user types and renders highlighted results", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("combobox", { name: "Search" }), "neural");

    expect(await screen.findByText("1 result in 3.2 ms")).toBeInTheDocument();
    const title = screen.getByRole("heading", { level: 3 });
    expect(title).toHaveTextContent("Deep Learning and Neural Networks");
    expect(title.querySelector("a")).toHaveAttribute("href", "https://example.com/dl");
    expect(screen.getAllByText("neural", { selector: "mark" })).toHaveLength(1);
    expect(screen.getByText("Informational")).toBeInTheDocument();
    await waitFor(() => expect(window.location.search).toBe("?q=neural"));

    const searchCalls = global.fetch.mock.calls.filter(([u]) => u.pathname === "/api/search");
    expect(searchCalls.length).toBe(1); // debounced: one request for the whole word
  });

  it("offers autocomplete suggestions", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByRole("combobox", { name: "Search" }), "neu");
    expect(await screen.findByRole("option", { name: "neural networks" })).toBeInTheDocument();
  });

  it("runs example queries immediately", async () => {
    const user = userEvent.setup();
    render(<App />);
    await act(() => user.click(screen.getByRole("button", { name: "machne lerning" })));
    await waitFor(() => {
      const calls = global.fetch.mock.calls.filter(([u]) => u.pathname === "/api/search");
      expect(calls[0][0].searchParams.get("q")).toBe("machne lerning");
    });
  });
});

describe("Highlight", () => {
  it("renders segments as text, never as HTML", () => {
    const { container } = render(<Highlight segments={[{ text: "<b>x</b>", highlight: true }]} />);
    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("mark").textContent).toBe("<b>x</b>");
  });
});
