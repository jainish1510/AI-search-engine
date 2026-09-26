# AI-Powered Search Engine

A full-stack search engine with NLP query processing, keyword extraction, a
MongoDB-backed inverted index and BM25F relevance ranking. It has a React
frontend that searches as you type.

| Layer    | Tech                                                        |
| -------- | ----------------------------------------------------------- |
| Frontend | React 19 + Vite (debounced live search, autocomplete)        |
| Backend  | Python, FastAPI (async REST API), Motor (async MongoDB)       |
| Storage  | MongoDB: documents, postings (inverted index), vocabulary    |
| NLP      | Custom analyzer, Snowball stemmer, RAKE + TF-IDF keywords    |

## Features

- **NLP query processing**: tokenization, accent folding, stop-word removal and
  stemming. Handles natural-language questions ("how do search engines rank
  results?"), strips conversational filler and detects intent (question,
  comparison, transactional, navigational or informational).
- **Query operators**: `"exact phrase"`, `-exclude`, `tag:name` and `title:word`.
- **Query expansion**: synonyms (car → automobile, k8s → kubernetes, …) are
  added with reduced weight.
- **Spelling correction**: Damerau-Levenshtein matching against the index
  vocabulary gives "Did you mean *machine learning*?".
- **Keyword extraction**: blends RAKE phrase scoring with TF-IDF computed
  against corpus document frequencies. It runs on every indexed document and is
  also available as `POST /api/analyze`.
- **Document indexing**: a positional inverted index in MongoDB (`postings`,
  `terms`, `vocab`, `stats` collections). Updates and deletes keep the index
  statistics consistent.
- **Relevance ranking**: BM25F with separate title/body weights and length
  normalization, a query-coverage factor, a term-proximity bonus and a phrase
  bonus.
- **Asynchronous search and dynamic results**: the async FastAPI/Motor backend
  runs bulk imports as background jobs you can poll. On the frontend, search
  runs as you type (debounced), stale requests are cancelled with
  `AbortController`, results highlight matches, and tag facets, query-analysis
  panels, pagination and shareable URLs are supported.

## Project layout

```
backend/
  app/
    nlp/          text analysis, query parser, keyword extraction, spelling
    services/     indexer, search/ranking, background jobs
    routers/      REST endpoints
    main.py       FastAPI app
    seed.py       sample data loader
  data/sample_documents.json
  tests/          pytest suite (NLP, ranking, API)
frontend/
  src/components  SearchBar, ResultCard, QueryInsights, Facets, AddDocuments, IndexPage…
  src/hooks.js    useDebounce / useAsync (abortable requests)
docker-compose.yml
```

## Running

### Docker (everything)

```bash
docker compose up --build
```

Open http://localhost:8080. The API is at http://localhost:8000/docs, and
sample documents are loaded on first start.

### Local development

Backend (needs a MongoDB at `mongodb://localhost:27017`):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed --reset          # load sample documents
uvicorn app.main:app --reload       # http://localhost:8000
```

No MongoDB? Run fully in memory (data is lost on restart):

```bash
MONGODB_URI=mongomock:// SEED_SAMPLE_DATA=1 uvicorn app.main:app --reload
```

Frontend (proxies `/api` to `localhost:8000`):

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

### Tests

```bash
cd backend && pytest               # 30 tests, in-memory MongoDB
cd frontend && npm test            # component tests (Vitest + Testing Library)
```

## Configuration

| Variable           | Default                                         |
| ------------------ | ----------------------------------------------- |
| `MONGODB_URI`      | `mongodb://localhost:27017` (`mongomock://` = in-memory) |
| `MONGODB_DB`       | `ai_search`                                     |
| `CORS_ORIGINS`     | `http://localhost:5173,http://localhost:3000`   |
| `SEED_SAMPLE_DATA` | unset; set to `true` to seed an empty database on startup |
| `VITE_API_URL`     | empty (same origin); frontend API base URL at build time |

## REST API

| Method | Path                     | Description                                         |
| ------ | ------------------------ | --------------------------------------------------- |
| GET    | `/api/search?q=&page=&size=&tags=&expand=` | Ranked results, snippets, facets, query analysis, did-you-mean |
| GET    | `/api/suggest?q=`        | Autocomplete from popular queries and vocabulary    |
| GET    | `/api/query/analyze?q=`  | How the NLP pipeline interprets a query             |
| POST   | `/api/analyze`           | Extract keywords/tokens from arbitrary text         |
| GET    | `/api/documents`         | List documents (paginated, `tag` filter)            |
| POST   | `/api/documents`         | Index one document `{title, body, url?, tags?}`     |
| POST   | `/api/documents/bulk`    | Queue many documents; returns a `job_id` (202)      |
| GET    | `/api/jobs/{id}`         | Bulk job progress                                   |
| GET/PATCH/DELETE | `/api/documents/{id}` | Read / re-index / remove a document       |
| GET    | `/api/stats`             | Corpus statistics, top words, popular queries       |
| GET    | `/api/health`            | Health check                                        |

Example:

```bash
curl 'localhost:8000/api/search?q=how+do+search+engines+rank+"inverted+index"+-docker'
```

## How ranking works

For each query term *t* and document *d*:

```
wtf(t,d) = w_title * tf_title / norm_title + w_body * tf_body / norm_body
norm_f   = 1 - b_f + b_f * len_f(d) / avg_len_f
score    = Σ weight(t) * idf(t) * wtf / (k1 + wtf)        (BM25F)
score   *= 0.4 + 0.6 * coverage²                           (share of query terms matched)
score   += 0.6 * matched_terms / min_span                  (proximity in body)
score   += 1.5 * mean idf(phrase terms)                    (for each quoted phrase)
```

Synonym-expansion terms get `weight = 0.35`. Phrases, `title:` terms,
exclusions and tags are hard filters.
