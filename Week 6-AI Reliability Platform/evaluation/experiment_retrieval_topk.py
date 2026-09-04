"""
Week 6, Experiment 3 — Retrieval Configuration (Top-K).

Actually RUNS the real `app.services.embedding_service.semantic_search`
(the same function `chat_routes.send_message` calls in production; it
falls back to TF-IDF exactly as it would offline without a Gemini key —
no mocking) against a seeded knowledge base with 2 relevant documents plus
3 topical decoys, so Top-K actually has room to matter. This replaces the
earlier narrative "(estimated)" version of this experiment with real
measured numbers.

Run: python -m evaluation.experiment_retrieval_topk
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models.models import db, Document, Chunk
from app.services import embedding_service
from config import Config

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")


class ExperimentConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tempfile.gettempdir(), "week6_topk_experiment.db")
    GEMINI_API_KEY = ""  # force the real TF-IDF fallback path, no network/mock needed


# 2 genuinely relevant documents (matching evaluation/dataset.jsonl's E-category
# ground truth) plus 3 topical decoys, so Top-K has room to make a difference.
SEED_DOCS = {
    "eiffel.txt": "The Eiffel Tower is 330 metres tall and located in Paris, France. "
                    "It was completed in 1889 for the World's Fair.",
    "eiffel3.txt": "The Eiffel Tower, located in Paris, stands 330 metres tall including "
                     "antennas and was finished in 1889.",
    "leaning_tower.txt": "The Leaning Tower of Pisa is a freestanding bell tower in the city "
                           "of Pisa, Italy, famous worldwide for its tilt.",
    "statue_of_liberty.txt": "The Statue of Liberty is a colossal statue on Liberty Island in "
                               "New York Harbor, a gift from France dedicated in 1886.",
    "great_wall.txt": "The Great Wall of China is a series of fortifications built across "
                        "northern China to protect against invasions.",
    "colosseum.txt": "The Colosseum is an ancient amphitheatre in the centre of Rome, Italy, "
                       "built of concrete and stone, completed around AD 80.",
}

QUERIES = [
    ("What is the Eiffel Tower's height?", {"eiffel.txt", "eiffel3.txt"}),
    ("Summarize everything about the Eiffel Tower.", {"eiffel.txt", "eiffel3.txt"}),
]


def _seed(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        from app.models.models import User, Workspace
        user = User(username="topk_experiment", email="topk@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        ws = Workspace(name="TopK Experiment", user_id=user.id)
        db.session.add(ws)
        db.session.commit()

        chunks = []
        for fname, content in SEED_DOCS.items():
            doc = Document(workspace_id=ws.id, filename=fname, filetype="txt",
                             filepath=f"/tmp/{fname}", char_count=len(content))
            db.session.add(doc)
            db.session.commit()
            chunk = Chunk(document_id=doc.id, chunk_index=0, content=content)
            db.session.add(chunk)
            db.session.commit()
            chunks.append(chunk)
        return [c.id for c in chunks]


def run_experiment():
    app = create_app(ExperimentConfig)
    chunk_ids = _seed(app)

    results = {}
    with app.app_context():
        all_chunks = Chunk.query.filter(Chunk.id.in_(chunk_ids)).all()
        id_to_filename = {c.id: c.document.filename for c in all_chunks}

        for top_k in (2, 4, 8):
            hits = 0
            total = 0
            precision_sum = 0.0
            chunks_returned_sum = 0
            for query, expected_docs in QUERIES:
                ranked = embedding_service.semantic_search(query, all_chunks, top_k=top_k)
                retrieved_docs = {id_to_filename[r["chunk"].id] for r in ranked}
                total += 1
                hit = expected_docs.issubset(retrieved_docs)
                hits += 1 if hit else 0
                precision = (len(retrieved_docs & expected_docs) / len(retrieved_docs)) if retrieved_docs else 0.0
                precision_sum += precision
                chunks_returned_sum += len(ranked)
            results[f"top_k={top_k}"] = {
                "retrieval_hit_rate": round(hits / total, 4),
                "avg_context_precision": round(precision_sum / total, 4),
                "avg_chunks_returned": round(chunks_returned_sum / total, 2),
            }

    os.makedirs(REPORTS_DIR, exist_ok=True)
    out_path = os.path.join(REPORTS_DIR, "experiment_retrieval_topk.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results, out_path


if __name__ == "__main__":
    results, path = run_experiment()
    print(json.dumps(results, indent=2))
    print(f"\nWritten to {path}")
