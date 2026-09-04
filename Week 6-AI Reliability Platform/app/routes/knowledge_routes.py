import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models.models import db, Document, Chunk
from app.services import document_service, embedding_service, gemini_service
from app.services.log_service import log_event
from app.routes.workspace_routes import get_accessible_workspace_or_404

knowledge_bp = Blueprint("knowledge", __name__, url_prefix="/workspaces/<int:workspace_id>/knowledge")


@knowledge_bp.route("/")
@login_required
def list_documents(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    documents = Document.query.filter_by(workspace_id=ws.id).order_by(Document.uploaded_at.desc()).all()
    return render_template("knowledge.html", ws=ws, documents=documents)


@knowledge_bp.route("/upload", methods=["POST"])
@login_required
def upload_document(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    file = request.files.get("document")

    if not file or file.filename == "":
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))

    if not document_service.allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash("Unsupported file type. Allowed: PDF, DOCX, TXT, MD.", "error")
        return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))

    filename = secure_filename(file.filename)
    filetype = filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    workspace_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(ws.id))
    os.makedirs(workspace_folder, exist_ok=True)
    filepath = os.path.join(workspace_folder, unique_name)
    file.save(filepath)

    try:
        text = document_service.extract_text(filepath, filetype)
    except Exception as exc:
        flash(f"Could not read file: {exc}", "error")
        return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))

    document = Document(
        workspace_id=ws.id, filename=filename, filetype=filetype,
        filepath=filepath, char_count=len(text),
    )
    db.session.add(document)
    db.session.flush()  # get document.id

    raw_chunks = document_service.chunk_text(
        text, current_app.config["CHUNK_SIZE"], current_app.config["CHUNK_OVERLAP"]
    )
    chunk_objs = []
    for idx, content in enumerate(raw_chunks):
        c = Chunk(document_id=document.id, chunk_index=idx, content=content)
        db.session.add(c)
        chunk_objs.append(c)

    db.session.commit()

    embedded_count = embedding_service.embed_chunks(chunk_objs, model=current_app.config["GEMINI_EMBEDDING_MODEL"])
    db.session.commit()

    try:
        document.summary = gemini_service.summarize(text, model=ws.model)
    except Exception:
        document.summary = "(Summary unavailable)"
    db.session.commit()

    log_event(
        "upload", f"Uploaded document '{filename}' ({len(raw_chunks)} chunks, {embedded_count} embedded)",
        user_id=current_user.id, workspace_id=ws.id,
    )
    flash(f"'{filename}' uploaded and indexed ({len(raw_chunks)} chunks).", "success")
    return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))


@knowledge_bp.route("/<int:document_id>/delete", methods=["POST"])
@login_required
def delete_document(workspace_id, document_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    document = Document.query.get_or_404(document_id)
    if document.workspace_id != ws.id:
        flash("Not found.", "error")
        return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))

    try:
        if os.path.exists(document.filepath):
            os.remove(document.filepath)
    except OSError:
        pass

    db.session.delete(document)
    db.session.commit()
    flash("Document removed.", "info")
    return redirect(url_for("knowledge.list_documents", workspace_id=ws.id))


@knowledge_bp.route("/search")
@login_required
def search_documents(workspace_id):
    ws = get_accessible_workspace_or_404(workspace_id)
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})

    chunks = (
        Chunk.query.join(Document, Chunk.document_id == Document.id)
        .filter(Document.workspace_id == ws.id).all()
    )
    results = embedding_service.semantic_search(query, chunks, top_k=6)
    payload = []
    for r in results:
        doc = Document.query.get(r["chunk"].document_id)
        payload.append({
            "document": doc.filename,
            "chunk_index": r["chunk"].chunk_index,
            "score": round(r["score"], 3),
            "snippet": r["chunk"].content[:250],
        })
    return jsonify({"results": payload})


@knowledge_bp.route("/<int:document_id>/ask", methods=["POST"])
@login_required
def ask_document(workspace_id, document_id):
    """Question answering scoped to a single document (Module 9)."""
    ws = get_accessible_workspace_or_404(workspace_id)
    document = Document.query.get_or_404(document_id)
    if document.workspace_id != ws.id:
        return jsonify({"error": "not found"}), 404

    question = (request.form.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    chunks = Chunk.query.filter_by(document_id=document.id).all()
    results = embedding_service.semantic_search(question, chunks, top_k=4)
    context = "\n\n".join(r["chunk"].content for r in results)

    system_prompt = (
        f"Answer the user's question using ONLY the provided document excerpts from "
        f"'{document.filename}'. If the answer isn't in the excerpts, say so clearly. "
        f"Cite chunk numbers you used.\n\nExcerpts:\n{context}"
    )
    result = gemini_service.chat_completion(
        system_prompt=system_prompt, history=[], user_message=question, model=ws.model,
    )
    log_event("search", f"Document Q&A on '{document.filename}'", user_id=current_user.id, workspace_id=ws.id,
              input_tokens=result["input_tokens"], output_tokens=result["output_tokens"])
    return jsonify({
        "answer": result["text"],
        "sources": [{"chunk_index": r["chunk"].chunk_index, "score": round(r["score"], 3)} for r in results],
    })
