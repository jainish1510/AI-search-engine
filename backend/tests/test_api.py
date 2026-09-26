import asyncio


async def test_document_crud_and_index_maintenance(client, db):
    res = await client.post(
        "/api/documents",
        json={"title": "Quantum Computing Primer", "body": "Qubits use superposition and entanglement.", "tags": ["Physics"]},
    )
    assert res.status_code == 201
    doc = res.json()
    assert doc["tags"] == ["physics"]
    assert any("qubits" in k["text"] or "quantum" in k["text"] for k in doc["keywords"])

    res = await client.get("/api/search", params={"q": "qubit superposition"})
    assert res.json()["results"][0]["id"] == doc["id"]

    res = await client.patch(f"/api/documents/{doc['id']}", json={"body": "Photonic chips and lasers."})
    assert res.status_code == 200
    assert (await client.get("/api/search", params={"q": "superposition"})).json()["total"] == 0
    assert (await client.get("/api/search", params={"q": "photonic"})).json()["total"] == 1

    assert (await client.delete(f"/api/documents/{doc['id']}")).status_code == 204
    assert (await client.get(f"/api/documents/{doc['id']}")).status_code == 404
    stats = (await client.get("/api/stats")).json()
    assert stats["documents"] == 0 and stats["unique_terms"] == 0
    assert await db.postings.count_documents({}) == 0


async def test_validation_and_not_found(client):
    assert (await client.post("/api/documents", json={"title": "   "})).status_code == 422
    assert (await client.get("/api/documents/not-an-id")).status_code == 404
    assert (await client.delete("/api/documents/64b000000000000000000000")).status_code == 404


async def test_bulk_index_job(client):
    docs = [{"title": f"Doc {i}", "body": f"bulk indexed content number{i}"} for i in range(5)]
    res = await client.post("/api/documents/bulk", json={"documents": docs})
    assert res.status_code == 202
    job_id = res.json()["job_id"]
    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] == "completed":
            break
        await asyncio.sleep(0.01)
    assert job["status"] == "completed" and job["processed"] == 5 and job["failed"] == 0
    assert (await client.get("/api/search", params={"q": "bulk content"})).json()["total"] == 5
    assert (await client.get("/api/documents", params={"size": 2})).json()["total"] == 5


async def test_suggest_and_analyze(client, seeded_db):
    await client.get("/api/search", params={"q": "neural networks"})
    suggestions = (await client.get("/api/suggest", params={"q": "neu"})).json()["suggestions"]
    assert suggestions[0] == "neural networks"  # popular past query first
    assert "neural" in suggestions
    assert "machine learning" in (await client.get("/api/suggest", params={"q": "machine lea"})).json()["suggestions"]

    analysis = (await client.get("/api/query/analyze", params={"q": 'what is "deep learning" -python'})).json()
    assert analysis["phrases"] == ["deep learning"] and analysis["excluded"] == ["python"]

    res = await client.post("/api/analyze", json={"text": "Search engines use inverted indexes. Inverted indexes map terms."})
    assert res.status_code == 200
    assert res.json()["keywords"][0]["text"] == "inverted indexes"


async def test_search_response_shape(client, seeded_db):
    body = (await client.get("/api/search", params={"q": "mongodb database"})).json()
    top = body["results"][0]
    assert top["title"] == "MongoDB Basics for Developers"
    assert set(top) >= {"id", "title", "title_segments", "snippet", "score", "relevance", "tags", "keywords", "url"}
    assert top["relevance"] == 1.0
    assert any(seg["highlight"] for seg in top["snippet"])
    assert body["took_ms"] >= 0 and body["pages"] >= 1
