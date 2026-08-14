from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.workspaces import _get_owned_workspace
from app.db.session import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.schemas.knowledge import AskRequest, AskResponse, DocumentOut, SearchResult
from app.services.knowledge.rag_service import build_grounded_context, ingest_document, save_upload, semantic_search
from app.services.llm.factory import get_provider

router = APIRouter(prefix="/api/workspaces/{workspace_id}/documents", tags=["documents"])

ALLOWED_TYPES = {"pdf", "docx", "txt", "md", "markdown"}


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_TYPES}")

    content = await file.read()
    file_path, file_type = save_upload(workspace_id, file.filename, content)

    document = Document(workspace_id=workspace_id, filename=file.filename, file_type=file_type,
                         file_path=file_path, status="pending")
    db.add(document)
    db.commit()
    db.refresh(document)

    ingest_document(db, document)
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    return db.query(Document).filter(Document.workspace_id == workspace_id).all()


@router.delete("/{document_id}", status_code=204)
def delete_document(workspace_id: str, document_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    doc = db.get(Document, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()


@router.post("/{document_id}/summary", response_model=DocumentOut)
def summarize_document(workspace_id: str, document_id: str, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Document Summary: generate (and cache) an LLM summary of the whole
    document from its stored chunks. Cached on first call; subsequent calls
    return the same summary without re-generating."""
    _get_owned_workspace(workspace_id, db, user)
    doc = db.get(Document, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.summary:
        return doc

    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no indexed content to summarize")

    full_text = "\n".join(c.content for c in chunks)[:12000]  # cap to keep prompt reasonable
    from app.core.config import get_settings
    provider = get_provider(model=get_settings().DEFAULT_MODEL)
    result = provider.generate(
        messages=[{"role": "user", "content": f"Summarize this document:\n\n{full_text}"}],
        system_prompt="You are a summarization assistant. Produce a concise, accurate summary preserving key facts.",
    )
    doc.summary = result.text
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/search/query", response_model=list[SearchResult])
def search_documents(workspace_id: str, q: str, top_k: int = 5, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    _get_owned_workspace(workspace_id, db, user)
    return semantic_search(db, workspace_id, q, top_k)


@router.post("/ask", response_model=AskResponse)
def ask_documents(workspace_id: str, payload: AskRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    """Document Q&A grounded in uploaded documents, with citations."""
    ws = _get_owned_workspace(workspace_id, db, user)
    results = semantic_search(db, workspace_id, payload.question, payload.top_k)
    if not results:
        return AskResponse(answer="No relevant documents found in this workspace yet.", sources=[])

    context = build_grounded_context(results)
    system_prompt = (
        "You are a document Q&A assistant. Answer ONLY using the provided context. "
        "If the context does not contain the answer, say so explicitly. Cite sources by filename."
    )
    prompt = f"Context:\n{context}\n\nQuestion: {payload.question}"

    from app.core.config import get_settings
    provider = get_provider(model=get_settings().DEFAULT_MODEL)
    result = provider.generate(messages=[{"role": "user", "content": prompt}], system_prompt=system_prompt)

    return AskResponse(answer=result.text, sources=[SearchResult(**r) for r in results])
