"""Document ingestion: text extraction + chunking (Module 5 / Module 9)."""
import os
from pypdf import PdfReader
import docx


def extract_text(filepath: str, filetype: str) -> str:
    filetype = filetype.lower()
    if filetype == "pdf":
        return _extract_pdf(filepath)
    if filetype == "docx":
        return _extract_docx(filepath)
    if filetype in ("txt", "md"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    raise ValueError(f"Unsupported file type: {filetype}")


def _extract_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract_docx(filepath: str) -> str:
    document = docx.Document(filepath)
    return "\n".join(p.text for p in document.paragraphs)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120):
    """Simple sliding-window character chunker. Returns list[str]."""
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
    return chunks


def allowed_file(filename: str, allowed_extensions) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
