"""Text extraction for supported document types: PDF, DOCX, TXT, Markdown."""
from __future__ import annotations

from pathlib import Path


def extract_text(file_path: str, file_type: str) -> str:
    file_type = file_type.lower()
    if file_type == "pdf":
        return _extract_pdf(file_path)
    if file_type == "docx":
        return _extract_docx(file_path)
    if file_type in ("txt", "md", "markdown"):
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {file_type}")


def _extract_pdf(file_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_path: str) -> str:
    import docx
    d = docx.Document(file_path)
    return "\n".join(p.text for p in d.paragraphs)
