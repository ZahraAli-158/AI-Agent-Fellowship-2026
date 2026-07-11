"""
Enterprise Document Intelligence Platform
==========================================
A Streamlit application implementing a RAG-based "chat with your documents"
enterprise knowledge assistant.

"""
import os
import sys
import uuid
import time

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from src.document_processor import process_document, ProcessedDocument, validate_file, recommend_chunk_size
from src.embeddings import get_embedding_function
from src.vector_store import VectorStore
from src.llm import get_llm, estimate_tokens
from src.chat_session import ChatSession
from src.utils import verify_user, register_user, load_users_db, save_users_db

load_dotenv()  # loads GEMINI_API_KEY (and any other secrets) from a local .env file, if present

# --------------------------------------------------------------------------
# Page config & constants
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Document Intelligence Platform",
    page_icon="\U0001F4DA",
    layout="wide",
    initial_sidebar_state="expanded",
)

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma")
USERS_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "users.json")
SUPPORTED_EXTENSIONS = ["pdf", "txt", "md", "markdown", "docx"]


# --------------------------------------------------------------------------
# Session state initialization
# --------------------------------------------------------------------------
def init_state():
    defaults = {
        "authenticated": False,
        "username": None,
        "users_db": load_users_db(USERS_DB_PATH),   # persisted across restarts — see data/users.json
        "dark_mode": True,
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),   # backend-only, never edited from the UI
        "embedding_provider": "gemini" if os.environ.get("GEMINI_API_KEY") else "local",
        "documents": {},                 # doc_id -> ProcessedDocument
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 4,
        "use_hybrid": False,
        "hybrid_weight": 0.6,
        "vector_store": None,
        "embedding_fn": None,
        "llm": None,
        "chat_session": None,
        "last_retrieved": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# --------------------------------------------------------------------------
# Styling (dark mode bonus feature)
# --------------------------------------------------------------------------
def inject_css():
    if st.session_state.dark_mode:
        bg, panel, panel2, text, accent, border = "#0F1117", "#181B24", "#1D212C", "#E6E8EE", "#6C8CFF", "#2A2E3A"
        shadow = "0 1px 3px rgba(0,0,0,0.35)"
    else:
        bg, panel, panel2, text, accent, border = "#FFFFFF", "#F7F8FA", "#FFFFFF", "#1A202C", "#2B6CB0", "#E2E8F0"
        shadow = "0 1px 3px rgba(0,0,0,0.06)"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        section[data-testid="stSidebar"] {{ background-color: {panel}; border-right: 1px solid {border}; }}

        h1, h2, h3 {{ letter-spacing: -0.01em; }}

        div[data-testid="stMetric"] {{
            background-color: {panel2}; border: 1px solid {border};
            border-radius: 12px; padding: 12px 14px; box-shadow: {shadow};
        }}
        div[data-testid="stMetric"] label {{ opacity: 0.75; font-size: 12.5px; }}

        .doc-card {{
            background-color: {panel2}; border: 1px solid {border}; border-radius: 12px;
            padding: 12px 14px; margin-bottom: 10px; box-shadow: {shadow};
            transition: border-color 0.15s ease;
        }}
        .doc-card:hover {{ border-color: {accent}66; }}

        .source-chip {{
            display: inline-block; background-color: {accent}1A; color: {accent};
            border: 1px solid {accent}44; border-radius: 999px; padding: 3px 10px;
            font-size: 11.5px; margin: 3px 5px 0 0; font-weight: 500;
        }}

        .status-ready {{ color: #2f855a; font-weight: 600; }}
        .status-error {{ color: #c53030; font-weight: 600; }}
        .status-processing {{ color: #c05621; font-weight: 600; }}

        /* Chat bubbles */
        div[data-testid="stChatMessage"] {{
            background-color: {panel2}; border: 1px solid {border};
            border-radius: 14px; padding: 4px 6px; box-shadow: {shadow};
        }}

        /* Buttons: slightly rounder, consistent with cards */
        .stButton > button {{ border-radius: 9px; }}

        /* Tabs: a touch more breathing room */
        button[data-baseweb="tab"] {{ padding-top: 8px; padding-bottom: 8px; }}

        /* Sidebar section captions */
        section[data-testid="stSidebar"] .stCaption {{ opacity: 0.8; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# --------------------------------------------------------------------------
# Auth (feature 1 — optional bonus, simulated sessions)
# --------------------------------------------------------------------------
def login_screen():
    st.title("\U0001F4DA Enterprise Document Intelligence Platform")
    st.caption("Sign in to continue. Accounts are saved locally (data/users.json, password hashed) "
               "so you won't need to re-register each time — this is still a demo-grade auth system, not production security.")

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                if verify_user(st.session_state.users_db, username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.chat_session = ChatSession(username)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        if st.button("Continue as guest"):
            st.session_state.authenticated = True
            st.session_state.username = "guest"
            st.session_state.chat_session = ChatSession("guest")
            st.rerun()

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Choose a username")
            new_pass = st.text_input("Choose a password", type="password")
            reg_submitted = st.form_submit_button("Create account", use_container_width=True)
            if reg_submitted:
                if register_user(st.session_state.users_db, new_user, new_pass):
                    save_users_db(st.session_state.users_db, USERS_DB_PATH)
                    st.success("Account created and saved — please sign in.")
                else:
                    st.error("Username is taken or fields are empty.")


# --------------------------------------------------------------------------
# Lazy singletons (embedding fn / vector store / llm), rebuilt when settings change
# --------------------------------------------------------------------------
def get_embedding_fn():
    key = st.session_state.gemini_api_key
    provider = st.session_state.embedding_provider
    cache_key = f"{provider}:{bool(key)}"
    if st.session_state.embedding_fn is None or st.session_state.get("_emb_cache_key") != cache_key:
        st.session_state.embedding_fn = get_embedding_function(provider, api_key=key)
        st.session_state["_emb_cache_key"] = cache_key
    return st.session_state.embedding_fn


def get_vector_store():
    emb_fn = get_embedding_fn()
    if st.session_state.vector_store is None or st.session_state.get("_vs_cache_key") != id(emb_fn):
        os.makedirs(PERSIST_DIR, exist_ok=True)
        # Each provider gets its own collection because embedding vectors from
        # different providers/models have different, incompatible dimensions
        # (e.g. local TF-IDF = 512 vs Gemini gemini-embedding-001 = 3072).
        # Mixing them in one ChromaDB collection raises a dimension error.
        collection_name = f"documents_{st.session_state.embedding_provider}"
        st.session_state.vector_store = VectorStore(PERSIST_DIR, emb_fn, collection_name=collection_name)
        st.session_state["_vs_cache_key"] = id(emb_fn)
    return st.session_state.vector_store


def get_llm_client():
    key = st.session_state.gemini_api_key
    provider = "gemini" if (st.session_state.embedding_provider == "gemini" and key) else "offline"
    cache_key = f"{provider}:{bool(key)}"
    if st.session_state.llm is None or st.session_state.get("_llm_cache_key") != cache_key:
        st.session_state.llm = get_llm(provider, api_key=key)
        st.session_state["_llm_cache_key"] = cache_key
    return st.session_state.llm


# --------------------------------------------------------------------------
# Sidebar: settings, document library, statistics
# --------------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.markdown(f"### \U0001F44B {st.session_state.username}")
        if st.button("Log out", use_container_width=True):
            for k in ["authenticated", "username", "chat_session"]:
                st.session_state[k] = False if k == "authenticated" else None
            st.rerun()

        st.divider()
        st.markdown("#### \u2699\ufe0f Settings")
        st.session_state.dark_mode = st.toggle("Dark mode", value=st.session_state.dark_mode)

        st.session_state.embedding_provider = st.selectbox(
            "Embedding / LLM provider",
            options=["local", "gemini"],
            index=0 if st.session_state.embedding_provider == "local" else 1,
            format_func=lambda x: "Gemini (backend key)" if x == "gemini" else "Local TF-IDF (offline demo)",
            help="Gemini gives true semantic embeddings and generated answers. "
                 "Local mode works fully offline using TF-IDF and extractive answers.",
        )
        # The API key itself is never entered or displayed in the UI — it is
        # read only from the backend .env file (see .env.example). This keeps
        # the key off the screen and out of any screenshots/screen shares.
        if st.session_state.embedding_provider == "gemini":
            if st.session_state.gemini_api_key:
                st.caption("\u2705 Gemini API key loaded from backend (.env) — not shown here.")
            else:
                st.caption(
                    "\u26a0\ufe0f No backend Gemini key found. Add `GEMINI_API_KEY=...` to a `.env` "
                    "file next to app.py and restart the app."
                )

        with st.expander("Chunking parameters"):
            st.session_state.chunk_size = st.slider("Chunk size (characters)", 200, 1500, st.session_state.chunk_size, 50)
            st.session_state.chunk_overlap = st.slider("Chunk overlap (characters)", 0, 300, st.session_state.chunk_overlap, 10)

        with st.expander("Retrieval settings"):
            st.session_state.top_k = st.slider("Chunks to retrieve (top-k)", 1, 10, st.session_state.top_k)
            st.session_state.use_hybrid = st.toggle("Hybrid search (semantic + keyword)", value=st.session_state.use_hybrid)
            if st.session_state.use_hybrid:
                st.session_state.hybrid_weight = st.slider(
                    "Semantic weight (vs. keyword)", 0.0, 1.0, st.session_state.hybrid_weight, 0.05
                )

        st.divider()
        st.markdown("#### \U0001F4C2 Document Library")
        docs = st.session_state.documents
        if not docs:
            st.caption("No documents uploaded yet.")
        else:
            for doc_id, doc in list(docs.items()):
                status_class = f"status-{doc.status}"
                with st.container():
                    st.markdown(
                        f'<div class="doc-card"><b>{doc.doc_name}</b><br>'
                        f'<span class="{status_class}">{doc.status.upper()}</span> \u00b7 '
                        f'{doc.num_pages} page(s) \u00b7 {len(doc.chunks)} chunk(s)</div>',
                        unsafe_allow_html=True,
                    )
                    c1, c2 = st.columns(2)
                    if c1.button("Refresh", key=f"refresh_{doc_id}", use_container_width=True):
                        refresh_document(doc_id)
                    if c2.button("Delete", key=f"delete_{doc_id}", use_container_width=True):
                        delete_document(doc_id)
                        st.rerun()

        st.divider()
        st.markdown("#### \U0001F4CA Statistics")
        llm = get_llm_client()
        total_chunks = sum(len(d.chunks) for d in docs.values())
        col1, col2 = st.columns(2)
        col1.metric("Documents", len(docs))
        col2.metric("Chunks indexed", total_chunks)
        col3, col4 = st.columns(2)
        col3.metric("Tokens used", llm.total_input_tokens + llm.total_output_tokens)
        col4.metric("Est. cost (USD)", f"${llm.cost_estimate_usd():.4f}")


# --------------------------------------------------------------------------
# Document processing actions
# --------------------------------------------------------------------------
def process_uploaded_files(uploaded_files):
    vector_store = get_vector_store()
    for f in uploaded_files:
        file_bytes = f.read()

        # --- Bonus: validate before touching the pipeline at all ---
        validation_error = validate_file(f.name, file_bytes)
        if validation_error:
            st.error(f"\u274c **{f.name}** rejected: {validation_error}")
            continue

        doc_id = str(uuid.uuid4())[:8]
        with st.status(f"Processing {f.name}...", expanded=True) as status:
            def on_progress(stage_text, _status=status):
                _status.write(f"\u2022 {stage_text}")

            on_progress("Reading file...")
            doc = process_document(
                doc_id=doc_id,
                filename=f.name,
                file_bytes=file_bytes,
                chunk_size=st.session_state.chunk_size,
                overlap=st.session_state.chunk_overlap,
                progress_callback=on_progress,
            )
            st.session_state.documents[doc_id] = doc

            if doc.status == "ready":
                on_progress("Generating embeddings...")
                vector_store.add_chunks(doc.chunks)
                on_progress("Storing in vector database...")
                status.update(
                    label=f"\u2705 {f.name} — {doc.num_pages} page(s), {len(doc.chunks)} chunk(s) indexed",
                    state="complete", expanded=False,
                )
            else:
                status.update(label=f"\u274c {f.name} failed: {doc.error_message}", state="error", expanded=True)


def delete_document(doc_id: str):
    vector_store = get_vector_store()
    vector_store.delete_document(doc_id)
    st.session_state.documents.pop(doc_id, None)


def refresh_document(doc_id: str):
    """Bonus: re-embed a document's existing chunks (e.g. after switching provider)."""
    doc = st.session_state.documents.get(doc_id)
    if not doc:
        return
    vector_store = get_vector_store()
    with st.spinner(f"Refreshing embeddings for {doc.doc_name}..."):
        vector_store.refresh_document(doc_id, doc.chunks)
    st.success(f"Refreshed embeddings for {doc.doc_name}.")


_NO_ANSWER_PHRASES = (
    "insufficient evidence", "do not contain", "does not contain", "doesn't contain",
    "not contain information", "no information", "cannot find", "can't find",
    "could not find", "couldn't find", "not mentioned", "not covered",
    "not available in the", "context does not", "context passages do not",
)


def answer_found_no_evidence(answer_text: str) -> bool:
    """Heuristic: did the LLM itself say it couldn't find the answer? Used to
    avoid showing a misleading confidence percentage next to an
    'insufficient evidence' response — retrieval always returns its closest
    available chunks even when none of them are actually relevant."""
    lowered = answer_text.lower()
    return any(phrase in lowered for phrase in _NO_ANSWER_PHRASES)


def show_llm_error(e: Exception):
    """Show a friendly message instead of letting API errors (quota, auth,
    network) crash the whole Streamlit app."""
    msg = str(e)
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
        st.error(
            "\u26a0\ufe0f Gemini API quota exceeded for your key/project. This is a Google "
            "account/billing limit, not an app bug. Try again in a minute, check your quota at "
            "https://ai.dev/rate-limit, or switch the sidebar provider to **Local TF-IDF "
            "(offline demo)** to keep working meanwhile."
        )
    elif "API key" in msg or "401" in msg or "PERMISSION_DENIED" in msg:
        st.error(
            "\u26a0\ufe0f Gemini rejected the API key (invalid or missing permissions). "
            "Double-check the key in the sidebar, or generate a new one at "
            "https://aistudio.google.com/apikey."
        )
    else:
        st.error(f"\u26a0\ufe0f The LLM request failed: {msg}")


def full_text_of(doc: ProcessedDocument) -> str:
    return "\n\n".join(p.text for p in doc.pages)


# --------------------------------------------------------------------------
# Main dashboard
# --------------------------------------------------------------------------
def main_dashboard():
    st.title("\U0001F4DA Enterprise Document Intelligence Platform")
    st.caption("Upload documents, then ask natural-language questions grounded in their content.")

    tab_workspace, tab_compare, tab_export = st.tabs(["\U0001F5C2\ufe0f Workspace", "\U0001F500 Compare Documents", "\U0001F4E4 Export Chat"])

    with tab_workspace:
        col_left, col_right = st.columns([1, 1.4], gap="large")

        with col_left:
            st.subheader("\U0001F4E4 Upload Panel")
            uploaded_files = st.file_uploader(
                "Upload PDF, TXT, Markdown, or DOCX files",
                type=SUPPORTED_EXTENSIONS,
                accept_multiple_files=True,
            )

            if uploaded_files:
                total_bytes = sum(f.size for f in uploaded_files)
                suggested = recommend_chunk_size(total_bytes)
                if suggested != st.session_state.chunk_size:
                    c1, c2 = st.columns([3, 1])
                    c1.info(
                        f"\U0001F4A1 Based on the size of these file(s) ({total_bytes/1024:.0f} KB), "
                        f"a chunk size of **{suggested}** characters is suggested "
                        f"(current setting: {st.session_state.chunk_size})."
                    )
                    if c2.button("Use it", use_container_width=True):
                        st.session_state.chunk_size = suggested
                        st.rerun()

            if uploaded_files and st.button("Process documents", type="primary", use_container_width=True):
                process_uploaded_files(uploaded_files)

            st.subheader("\u23f3 Processing Status")
            docs = st.session_state.documents
            if not docs:
                st.caption("Nothing processed yet.")
            else:
                for doc in docs.values():
                    icon = {"ready": "\u2705", "error": "\u274c", "processing": "\u23f3", "pending": "\u23f8\ufe0f"}[doc.status]
                    st.write(f"{icon} **{doc.doc_name}** — {doc.status} "
                             f"({doc.num_pages} pages, {len(doc.chunks)} chunks)")
                    if doc.status == "ready":
                        with st.expander("Auto-summary & suggested questions"):
                            if st.button("Generate", key=f"gen_{doc.doc_id}"):
                                llm = get_llm_client()
                                sample = full_text_of(doc)
                                try:
                                    summary = llm.summarize_document(sample, doc.doc_name)
                                    questions = llm.suggest_questions(sample, doc.doc_name)
                                    st.session_state[f"summary_{doc.doc_id}"] = summary
                                    st.session_state[f"questions_{doc.doc_id}"] = questions
                                except Exception as e:  # noqa: BLE001
                                    show_llm_error(e)
                            if f"summary_{doc.doc_id}" in st.session_state:
                                st.markdown(f"**Summary:** {st.session_state[f'summary_{doc.doc_id}']}")
                                st.markdown("**Try asking:**")
                                for q in st.session_state[f"questions_{doc.doc_id}"]:
                                    st.markdown(f"- {q}")

        with col_right:
            st.subheader("\U0001F4AC Chat Window")
            chat_container = st.container(height=420, border=True)
            with chat_container:
                for turn in st.session_state.chat_session.history:
                    with st.chat_message(turn.role):
                        st.markdown(turn.content)
                        if turn.sources:
                            def _page_str(s):
                                p = s["metadata"].get("page_number", -1)
                                return str(p) if p and p != -1 else "N/A"

                            if turn.role == "assistant" and answer_found_no_evidence(turn.content):
                                st.markdown(
                                    '<span style="color:#c53030; font-weight:600; font-size:12.5px;">'
                                    '\u26a0 No strong match found in the documents</span>'
                                    '<span style="color:#888; font-size:11.5px;"> — the passages below were '
                                    'the closest available, but the model judged none of them '
                                    'sufficient to answer confidently</span>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                top_score = max((s["score"] for s in turn.sources), default=0.0)
                                conf_pct = min(100, round(top_score * 100))
                                if conf_pct >= 70:
                                    conf_color, conf_label = "#2f855a", "High"
                                elif conf_pct >= 40:
                                    conf_color, conf_label = "#c05621", "Medium"
                                else:
                                    conf_color, conf_label = "#c53030", "Low"
                                st.markdown(
                                    f'<span style="color:{conf_color}; font-weight:600; font-size:12.5px;">'
                                    f'\u25cf Confidence: {conf_pct}% ({conf_label})</span>'
                                    f'<span style="color:#888; font-size:11.5px;"> — based on how closely the '
                                    f'retrieved passages match your question</span>',
                                    unsafe_allow_html=True,
                                )
                            chips = "".join(
                                f'<span class="source-chip">{s["metadata"]["doc_name"]} '
                                f'(p.{_page_str(s)}, '
                                f'chunk {s["metadata"].get("chunk_index")})</span>'
                                for s in turn.sources
                            )
                            st.markdown(chips, unsafe_allow_html=True)

            with st.expander("\U0001F50E Metadata filter — search specific documents only"):
                doc_options = {doc.doc_name: doc_id for doc_id, doc in st.session_state.documents.items() if doc.status == "ready"}
                selected_names = st.multiselect("Limit search to:", options=list(doc_options.keys()))
                selected_doc_ids = [doc_options[n] for n in selected_names] or None

            question = st.chat_input("Ask a question about your documents...")
            if question:
                handle_question(question, selected_doc_ids)
                st.rerun()

            if st.session_state.last_retrieved:
                with st.expander("\U0001F4C4 Retrieved chunks used for the last answer", expanded=False):
                    for r in st.session_state.last_retrieved:
                        meta = r["metadata"]
                        page = meta.get("page_number", -1)
                        page_str = str(page) if page and page != -1 else "N/A"
                        st.markdown(
                            f"**{meta.get('doc_name')}** \u2014 page {page_str}, "
                            f"chunk {meta.get('chunk_index')} (score: {r['score']:.3f})"
                        )
                        st.caption(r["text"][:400] + ("..." if len(r["text"]) > 400 else ""))

    with tab_compare:
        st.subheader("\U0001F500 Document Comparison")
        ready_docs = {d.doc_name: d for d in st.session_state.documents.values() if d.status == "ready"}
        if len(ready_docs) < 2:
            st.info("Upload and process at least two documents to compare them.")
        else:
            c1, c2 = st.columns(2)
            name_a = c1.selectbox("Document A", options=list(ready_docs.keys()), key="cmp_a")
            name_b = c2.selectbox("Document B", options=list(ready_docs.keys()), index=1, key="cmp_b")
            if st.button("Compare", type="primary"):
                llm = get_llm_client()
                doc_a, doc_b = ready_docs[name_a], ready_docs[name_b]
                with st.spinner("Comparing documents..."):
                    try:
                        result = llm.compare_documents(name_a, full_text_of(doc_a), name_b, full_text_of(doc_b))
                        st.markdown(result)
                    except Exception as e:  # noqa: BLE001
                        show_llm_error(e)

    with tab_export:
        st.subheader("\U0001F4E4 Export Conversation")
        if not st.session_state.chat_session.history:
            st.info("No conversation yet — ask a question in the Workspace tab first.")
        else:
            md_export = st.session_state.chat_session.export_markdown()
            json_export = st.session_state.chat_session.export_json()
            c1, c2 = st.columns(2)
            c1.download_button("Download as Markdown", md_export, file_name="conversation.md", use_container_width=True)
            c2.download_button("Download as JSON", json_export, file_name="conversation.json", use_container_width=True)
            if st.button("Clear conversation"):
                st.session_state.chat_session.clear()
                st.rerun()


def handle_question(question: str, selected_doc_ids):
    vector_store = get_vector_store()
    llm = get_llm_client()
    chat = st.session_state.chat_session

    chat.add_user_message(question)

    if st.session_state.use_hybrid:
        retrieved = vector_store.hybrid_search(
            question, top_k=st.session_state.top_k, doc_ids=selected_doc_ids,
            semantic_weight=st.session_state.hybrid_weight,
        )
    else:
        retrieved = vector_store.semantic_search(question, top_k=st.session_state.top_k, doc_ids=selected_doc_ids)

    st.session_state.last_retrieved = retrieved

    try:
        answer = llm.answer_with_citations(question, retrieved, chat_history=chat.as_llm_history())
        chat.add_assistant_message(answer, sources=retrieved)
    except Exception as e:  # noqa: BLE001
        show_llm_error(e)
        chat.add_assistant_message(
            "\u26a0\ufe0f Sorry, the answer could not be generated due to an API error (see message above). "
            "The relevant passages were still retrieved and are shown below.",
            sources=retrieved,
        )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main():
    if not st.session_state.authenticated:
        login_screen()
    else:
        sidebar()
        main_dashboard()


if __name__ == "__main__":
    main()
