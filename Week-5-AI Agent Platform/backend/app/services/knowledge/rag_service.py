"""Document ingestion pipeline (upload -> extract -> chunk -> embed -> store)
and semantic search with citations."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.knowledge.chunker import chunk_text
from app.services.knowledge.embeddings import cosine_similarity, embed_text, embed_to_json
from app.services.knowledge.extractors import extract_text


def save_upload(workspace_id: str, filename: str, content: bytes) -> tuple[str, str]:
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR) / workspace_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(content)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    return str(dest), ext


def ingest_document(db: Session, document: Document) -> None:
    """Extract -> chunk -> embed -> persist. Updates document.status/num_chunks."""
    try:
        text = extract_text(document.file_path, document.file_type)
        pieces = chunk_text(text)
        for idx, piece in enumerate(pieces):
            db.add(Chunk(document_id=document.id, chunk_index=idx, content=piece,
                          embedding_json=embed_to_json(piece)))
        document.status = "embedded"
        document.num_chunks = len(pieces)
        db.commit()
    except Exception:
        document.status = "failed"
        db.commit()
        raise


def semantic_search(db: Session, workspace_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Return top_k chunks (with document filename + score) most similar to query,
    across all documents in the workspace, for grounded Q&A with citations."""
    query_vec = embed_text(query)

    chunks = (
        db.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Document.workspace_id == workspace_id, Document.status == "embedded")
        .all()
    )

    scored = []
    for chunk, doc in chunks:
        if not chunk.embedding_json:
            continue
        vec = json.loads(chunk.embedding_json)
        score = cosine_similarity(query_vec, vec)
        scored.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": score,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def build_grounded_context(results: list[dict]) -> str:
    """Format retrieved chunks into a citation-annotated context block for the LLM prompt."""
    lines = []
    for r in results:
        lines.append(f"[Source: {r['filename']} #chunk{r['chunk_index']}]\n{r['content']}")
    return "\n\n".join(lines)
