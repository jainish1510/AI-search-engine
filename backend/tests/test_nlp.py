from app.nlp import analyze, extract_keywords, parse_query, tokenize
from app.nlp.spelling import best_correction, damerau_levenshtein


def test_tokenize_removes_stop_words_but_keeps_positions():
    tokens = tokenize("The state of the art in Search")
    assert [t.surface for t in tokens] == ["state", "art", "search"]
    assert [t.position for t in tokens] == [1, 4, 6]


def test_stemming_and_accent_normalisation():
    assert analyze("Running runners ran") == ["run", "runner", "ran"]
    assert analyze("Café") == analyze("cafe")


def test_technical_identifiers_are_kept_intact():
    assert analyze("Node.js and C++ with python3") == ["node.js", "c++", "python3"]


def test_parse_query_operators():
    q = parse_query('how to deploy "react app" -kubernetes tag:DevOps title:guide')
    assert q.terms == ["deploy"]
    assert q.phrase_texts == ["react app"]
    assert q.phrases == [[("react", 0), ("app", 1)]]
    assert q.excluded == ["kubernet"]
    assert q.tags == ["devops"]
    assert q.title_terms == ["guid"]
    assert q.intent == "question" and q.is_question


def test_phrase_offsets_account_for_stop_words():
    q = parse_query('"state of the art"')
    assert q.phrases == [[("state", 0), ("art", 3)]]


def test_intent_detection():
    assert parse_query("react vs vue").intent == "comparison"
    assert parse_query("buy electric car").intent == "transactional"
    assert parse_query("python documentation").intent == "navigational"
    assert parse_query("renewable energy").intent == "informational"


def test_conversational_filler_is_removed():
    q = parse_query("can you please tell me about neural networks")
    assert q.terms == ["neural", "network"]


def test_synonym_expansion():
    q = parse_query("car")
    assert q.expansions["car"] == ["automobil", "vehicl"]
    assert parse_query("car", expand=False).expansions == {}


def test_keyword_extraction_prefers_phrases():
    text = (
        "Machine learning is a field of artificial intelligence. Machine learning algorithms "
        "build models from training data. Artificial intelligence research is growing."
    )
    keywords = [k.text for k in extract_keywords(text, top_k=5)]
    assert any(k.startswith("artificial intelligence") for k in keywords)
    assert any(k.startswith("machine learning") for k in keywords)
    assert "is" not in keywords


def test_keyword_extraction_uses_idf():
    text = "Python is a language. Python is popular. Snakes are reptiles."
    without_idf = extract_keywords(text, top_k=5)
    with_idf = extract_keywords(text, top_k=5, doc_freq=lambda t: 100 if t == "python" else 1, total_docs=100)
    assert without_idf[0].text == "python"
    assert with_idf[-1].text == "python"  # appears in every document, so it drops to last


def test_edit_distance_and_correction():
    assert damerau_levenshtein("serach", "search") == 1
    assert damerau_levenshtein("kitten", "sitting") == 3
    assert best_correction("serach", {"search": 5, "seraph": 1}) == "search"
    assert best_correction("cat", {"car": 3}) is None  # too short to correct


def test_domain_words_are_not_treated_as_filler():
    q = parse_query("how do search engines find information")
    assert q.terms == ["search", "engin", "inform"]
