"""
Embedding service.

Uses a stateless HashingVectorizer (scikit-learn) as the default embedding
backend so the platform works fully offline / without a paid embeddings API
call for every chunk -- important for a student project with limited API
quota. The interface (embed_text -> list[float]) is intentionally identical
to what a real embeddings API (Gemini text-embedding-004, OpenAI
text-embedding-3-small, etc.) would return, so swapping in a real API later
means changing only this file.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

_DIM = 256
_vectorizer = HashingVectorizer(n_features=_DIM, alternate_sign=False, norm="l2")


def embed_text(text: str) -> list[float]:
    vec = _vectorizer.transform([text]).toarray()[0]
    return vec.tolist()


def embed_to_json(text: str) -> str:
    return json.dumps(embed_text(text))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
