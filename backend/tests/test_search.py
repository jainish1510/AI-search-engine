from app.services.search import build_snippet, min_span, search


async def titles(db, q, **kw):
    res = await search(db, q, log=False, **kw)
    return [r["title"] for r in res["results"]], res


async def test_basic_relevance(seeded_db):
    found, res = await titles(seeded_db, "inverted index")
    assert found[0] == "Building an Inverted Index"
    assert res["total"] >= 2


async def test_title_matches_rank_higher(seeded_db):
    found, _ = await titles(seeded_db, "docker")
    assert found[0] == "Docker for Beginners"


async def test_natural_language_question(seeded_db):
    found, res = await titles(seeded_db, "how do search engines rank results?")
    assert found[0] == "How Search Engines Rank Results"
    assert res["analysis"]["intent"] == "question"


async def test_phrase_query_requires_adjacency(seeded_db):
    found, _ = await titles(seeded_db, '"neural networks"')
    assert found and all("neural" in t.lower() or "learning" in t.lower() for t in found)
    none, res = await titles(seeded_db, '"networks neural"')
    assert none == [] and res["total"] == 0


async def test_exclusion(seeded_db):
    found, _ = await titles(seeded_db, "react")
    assert "React Hooks Deep Dive" in found
    found, _ = await titles(seeded_db, "javascript -react")
    assert "Node.js Event Loop and Asynchronous Programming" in found
    assert not any("React" in t for t in found)


async def test_tag_filter_and_facets(seeded_db):
    found, res = await titles(seeded_db, "search tag:nlp")
    assert found
    for r in res["results"]:
        assert "nlp" in r["tags"]
    _, res = await titles(seeded_db, "search", tags=["ai"])
    assert all("ai" in r["tags"] for r in res["results"])
    _, res = await titles(seeded_db, "search")
    assert any(f["tag"] == "search" for f in res["facets"])


async def test_tag_only_browse(seeded_db):
    found, res = await titles(seeded_db, "tag:energy")
    assert set(found) == {"Electric Cars and the Future of Transport", "Renewable Energy Sources"}


async def test_synonym_expansion_finds_related_docs(seeded_db):
    found, _ = await titles(seeded_db, "car")
    assert "Electric Cars and the Future of Transport" in found
    found, _ = await titles(seeded_db, "movie")
    assert "The History of the Film Industry" in found  # via "movies" and "film" synonym


async def test_did_you_mean(seeded_db):
    _, res = await titles(seeded_db, "machne lerning")
    assert res["did_you_mean"] == "machine learning"


async def test_pagination(seeded_db):
    _, first = await titles(seeded_db, "data", size=2)
    _, second = await titles(seeded_db, "data", size=2, page=2)
    assert first["total"] == second["total"] > 2
    assert {r["id"] for r in first["results"]}.isdisjoint({r["id"] for r in second["results"]})


async def test_empty_query(seeded_db):
    _, res = await titles(seeded_db, "   ")
    assert res["total"] == 0 and res["results"] == []


def test_snippet_highlights_best_window():
    text = " ".join(["filler"] * 50) + " the inverted index stores postings " + " ".join(["tail"] * 50)
    segments = build_snippet(text, {"invert", "index"}, max_words=12)
    highlighted = [s["text"] for s in segments if s["highlight"]]
    assert highlighted == ["inverted", "index"]
    assert segments[0]["text"] == "… " and segments[-1]["text"] == " …"


def test_min_span():
    assert min_span([[1, 10], [12], [4, 11]]) == 3
    assert min_span([[1], []]) is None
