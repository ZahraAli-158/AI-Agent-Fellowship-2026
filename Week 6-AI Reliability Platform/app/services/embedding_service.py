"""
Semantic search over document chunks.

Primary path: Gemini embeddings (models/gemini-embedding-001), cosine similarity.
Fallback path (no API key / embedding failure): TF-IDF + cosine similarity,
computed on the fly with scikit-learn so the Knowledge Base module still works
fully offline.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services import gemini_service


def embed_chunks(chunks, model):
    """Attach a Gemini embedding to each Chunk object where possible.
    Returns the count of chunks that got a real embedding (rest stay None
    and are covered by the TF-IDF fallback at query time)."""
    embedded = 0
    for chunk in chunks:
        vector = gemini_service.embed_text(chunk.content, model=model)
        if vector:
            chunk.set_embedding(vector)
            embedded += 1
    return embedded


def _semantic_search_gemini(query, chunks, model, top_k):
    query_vec = gemini_service.embed_text(query, model=model)
    if not query_vec:
        return None

    vectors, valid_chunks = [], []
    for c in chunks:
        v = c.get_embedding()
        if v:
            vectors.append(v)
            valid_chunks.append(c)

    if not vectors:
        return None

    sims = cosine_similarity([query_vec], vectors)[0]
    ranked = sorted(zip(valid_chunks, sims), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"chunk": c, "score": float(s)} for c, s in ranked]


def _semantic_search_tfidf(query, chunks, top_k):
    if not chunks:
        return []
    texts = [c.content for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=4096)
    try:
        matrix = vectorizer.fit_transform(texts + [query])
    except ValueError:
        return []
    query_vec = matrix[-1]
    doc_matrix = matrix[:-1]
    sims = cosine_similarity(query_vec, doc_matrix)[0]
    ranked = sorted(zip(chunks, sims), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"chunk": c, "score": float(s)} for c, s in ranked if s > 0]


def semantic_search(query, chunks, model="models/gemini-embedding-001", top_k=5):
    """Returns list of {chunk, score} sorted by relevance, using Gemini
    embeddings when available and falling back to TF-IDF otherwise."""
    if not chunks:
        return []

    result = _semantic_search_gemini(query, chunks, model, top_k)
    if result is not None:
        return result

    return _semantic_search_tfidf(query, chunks, top_k)
