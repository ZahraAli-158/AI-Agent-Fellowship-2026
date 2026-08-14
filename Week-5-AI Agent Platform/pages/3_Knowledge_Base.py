import streamlit as st

from api_client import get, post
from components import badge, empty_state, gradient_divider, page_header
from nav import require_workspace

require_workspace()
ws_id = st.session_state.workspace_id

page_header("📚", "Knowledge Base", "Upload documents and ground your assistant's answers in them")
gradient_divider()

st.markdown("#### Upload a Document")
with st.container(border=True):
    uploaded = st.file_uploader(
        "Drag and drop or browse",
        type=["pdf", "docx", "txt", "md"],
        help="Supported: PDF, DOCX, TXT, Markdown",
    )
    if uploaded and st.button("⬆️ Upload & Index", use_container_width=True):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        with st.spinner("Extracting text, chunking, and generating embeddings…"):
            doc = post(f"/api/workspaces/{ws_id}/documents", files=files)
        st.success(f"Indexed **{doc['filename']}** into {doc['num_chunks']} chunks")
        st.rerun()

gradient_divider()

st.markdown("#### Your Documents")
docs = get(f"/api/workspaces/{ws_id}/documents")
if docs:
    cols = st.columns(3)
    status_color = {"embedded": "green", "pending": "yellow", "failed": "red"}
    for i, d in enumerate(docs):
        with cols[i % 3]:
            with st.container(border=True):
                icon = {"pdf": "📕", "docx": "📘", "txt": "📄", "md": "📝"}.get(d["file_type"], "📄")
                st.markdown(f"### {icon}")
                st.markdown(f"**{d['filename']}**")
                st.markdown(badge(d["status"], status_color.get(d["status"], "purple")), unsafe_allow_html=True)
                st.markdown(
                    f"<span class='awp-muted' style='font-size:12px;'>{d['num_chunks']} chunks · "
                    f"{d['created_at'][:10]}</span>",
                    unsafe_allow_html=True,
                )
                if d.get("summary"):
                    with st.expander("📋 Summary"):
                        st.markdown(f"<span class='awp-muted'>{d['summary']}</span>", unsafe_allow_html=True)
                elif d["status"] == "embedded":
                    if st.button("📋 Generate Summary", key=f"sum_{d['id']}", use_container_width=True):
                        with st.spinner("Summarizing…"):
                            post(f"/api/workspaces/{ws_id}/documents/{d['id']}/summary")
                        st.rerun()
else:
    empty_state("📂", "No documents yet", "Upload a PDF, DOCX, TXT, or Markdown file above")

gradient_divider()

st.markdown("#### 🔎 Semantic Search")
query = st.text_input("Search across your documents", placeholder="e.g. refund policy timeline")
if query:
    results = get(f"/api/workspaces/{ws_id}/documents/search/query", params={"q": query})
    if not results:
        empty_state("🔍", "No matches found", "Try a different search phrase")
    for r in results:
        with st.container(border=True):
            st.markdown(
                f"**{r['filename']}** · chunk #{r['chunk_index']} · "
                f"<span style='color:#A855F7'>score {r['score']:.3f}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"<span class='awp-muted'>{r['content'][:400]}</span>", unsafe_allow_html=True)

gradient_divider()

st.markdown("#### ❓ Ask Your Documents")
question = st.text_input("Ask a grounded question", placeholder="What does the document say about…?")
if question and st.button("Ask", use_container_width=True):
    with st.spinner("Retrieving relevant context and generating an answer…"):
        result = post(f"/api/workspaces/{ws_id}/documents/ask", json={"question": question})
    with st.container(border=True):
        st.markdown(result["answer"])
        if result["sources"]:
            st.markdown("<div class='awp-muted' style='margin-top:10px; font-size:13px;'>Sources</div>",
                        unsafe_allow_html=True)
            for s in result["sources"]:
                st.caption(f"— {s['filename']} (chunk #{s['chunk_index']}, score {s['score']:.3f})")
