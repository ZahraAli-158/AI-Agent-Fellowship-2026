"""
Database models for the AI Workspace Platform.

Tables implemented (per project spec, section 9 - Database Design):
    Users, Workspaces, Conversations, Messages, Documents, Chunks,
    (Embeddings are stored as a JSON column on Chunk, see note below),
    PromptTemplates, Skills, SkillExecutions, MemoryItems, Settings, Logs
"""
from datetime import datetime
import json

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    workspaces = db.relationship("Workspace", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class Workspace(db.Model):
    """A user workspace (e.g. Marketing, Research, Programming, University, Business)."""

    __tablename__ = "workspaces"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), default="Custom")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_favorite = db.Column(db.Boolean, default=False)  # Advanced feature: Bookmarks/Favorites

    # --- Module 3: AI Assistant Configuration ---
    assistant_name = db.Column(db.String(120), default="Assistant")
    assistant_role = db.Column(db.String(200), default="A helpful general-purpose assistant")
    system_prompt = db.Column(db.Text, default="You are a helpful, concise, and honest AI assistant.")
    model = db.Column(db.String(80), default="gemini-3.6-flash")
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=1024)
    personality = db.Column(db.String(120), default="Friendly and professional")
    response_style = db.Column(db.String(120), default="Balanced")

    conversations = db.relationship("Conversation", backref="workspace", lazy=True, cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="workspace", lazy=True, cascade="all, delete-orphan")
    memory_items = db.relationship("MemoryItem", backref="workspace", lazy=True, cascade="all, delete-orphan")
    settings = db.relationship("Setting", backref="workspace", lazy=True, cascade="all, delete-orphan")
    shares = db.relationship("WorkspaceShare", backref="workspace", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "assistant_name": self.assistant_name,
            "model": self.model,
            "temperature": self.temperature,
            "is_favorite": self.is_favorite,
        }


class WorkspaceShare(db.Model):
    """Advanced feature: Workspace Sharing — grants another user access to a
    workspace they don't own. Kept to a single 'collaborator' role (can chat,
    upload documents, run skills, view the dashboard) for simplicity; only
    the workspace owner can change assistant settings, delete the workspace,
    or manage sharing itself."""

    __tablename__ = "workspace_shares"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    user = db.relationship("User", backref="shared_workspaces")
    role = db.Column(db.String(20), default="collaborator")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_share"),)


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    title = db.Column(db.String(200), default="New Conversation")
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    tags = db.Column(db.String(200), default="")

    messages = db.relationship("Message", backref="conversation", lazy=True, cascade="all, delete-orphan",
                                order_by="Message.created_at")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_pinned": self.is_pinned,
            "message_count": len(self.messages),
        }


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user | assistant | system
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    token_count = db.Column(db.Integer, default=0)
    citations = db.Column(db.Text, default="[]")  # JSON list of {document, chunk_id, snippet}

    def citations_list(self):
        try:
            return json.loads(self.citations or "[]")
        except json.JSONDecodeError:
            return []


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filetype = db.Column(db.String(10), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text, default="")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    char_count = db.Column(db.Integer, default=0)

    chunks = db.relationship("Chunk", backref="document", lazy=True, cascade="all, delete-orphan")


class Chunk(db.Model):
    """A chunk of a document plus its embedding vector (stored as JSON text)."""

    __tablename__ = "chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text, nullable=True)  # JSON-encoded float list (the "Embeddings" table)

    def get_embedding(self):
        if not self.embedding:
            return None
        return json.loads(self.embedding)

    def set_embedding(self, vector):
        self.embedding = json.dumps(vector)


class PromptTemplate(db.Model):
    __tablename__ = "prompt_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default="Custom")
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_count = db.Column(db.Integer, default=0)


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), default="")
    icon = db.Column(db.String(10), default="\U0001F9E9")
    prompt_template = db.Column(db.Text, nullable=False)


class SkillExecution(db.Model):
    __tablename__ = "skill_executions"

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    skill = db.relationship("Skill", backref="executions")
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    input_text = db.Column(db.Text, nullable=False)
    output_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_ms = db.Column(db.Integer, default=0)


class MemoryItem(db.Model):
    """Long-term memory entries: preferences, past discussions, FAQs, pinned info."""

    __tablename__ = "memory_items"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    category = db.Column(db.String(30), default="preference")  # preference | topic | discussion | pinned
    content = db.Column(db.Text, nullable=False)
    weight = db.Column(db.Integer, default=1)  # frequency / importance counter
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)


class Setting(db.Model):
    """Arbitrary key/value settings scoped to a workspace (theme, flags, etc.)."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, index=True)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.String(255), nullable=False)

    __table_args__ = (db.UniqueConstraint("workspace_id", "key", name="uq_workspace_setting"),)


class Log(db.Model):
    """Application / usage log for observability and cost monitoring (Module 10)."""

    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False)  # chat, upload, skill, auth, error, search
    message = db.Column(db.String(500), default="")
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    latency_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def estimated_cost(self, cfg):
        """`cfg` is a Flask app.config mapping (dict-like), not the Config class."""
        input_rate = cfg.get("COST_PER_1K_INPUT_TOKENS", 0.000075)
        output_rate = cfg.get("COST_PER_1K_OUTPUT_TOKENS", 0.0003)
        return round(
            (self.input_tokens / 1000.0) * input_rate
            + (self.output_tokens / 1000.0) * output_rate,
            6,
        )


# =====================================================================
# AGENTS — a separate system from Workspaces. Each agent (e.g. "Meeting
# Agent") has real tools it can call (create/list/update/delete/complete
# tasks, extract meeting notes, send email) via Gemini function-calling,
# not just a prompt template. Agent definitions (name/icon/system prompt/
# available tools) live in code (app/agents/registry.py); only the data
# they produce — tasks and conversations — is stored here.
# =====================================================================

class AgentTask(db.Model):
    """A task created/managed by an agent (or manually by the user) — the
    Meeting Agent's create_task/list_task/update_task/delete_task/
    complete_task tools all operate on this table."""

    __tablename__ = "agent_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    agent_key = db.Column(db.String(50), nullable=False, index=True)  # e.g. "meeting"
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="pending")  # pending | in_progress | completed
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.strftime("%b %d, %Y"),
        }


class AgentConversation(db.Model):
    __tablename__ = "agent_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    agent_key = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), default="New conversation")
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship("AgentMessage", backref="conversation", lazy=True,
                                cascade="all, delete-orphan", order_by="AgentMessage.created_at")


class AgentMessage(db.Model):
    __tablename__ = "agent_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("agent_conversations.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # user | assistant
    content = db.Column(db.Text, nullable=False)
    tool_calls = db.Column(db.Text, default="[]")  # JSON list of {tool, args, result} for transparency
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def tool_calls_list(self):
        try:
            return json.loads(self.tool_calls or "[]")
        except json.JSONDecodeError:
            return []


# ---------------------------------------------------------------------------
# Week 6 — Reliability & Observability layer
# ---------------------------------------------------------------------------

class Trace(db.Model):
    """One row per end-to-end AI request. See app/observability/tracing.py."""

    __tablename__ = "traces"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_id = db.Column(db.String(64), nullable=True, index=True)
    workspace_id = db.Column(db.Integer, nullable=True, index=True)
    model = db.Column(db.String(80), default="")
    prompt_version = db.Column(db.String(20), default="")
    request_type = db.Column(db.String(30), default="chat")  # chat | agent | rag | eval
    agent_key = db.Column(db.String(50), nullable=True, index=True)  # e.g. "meeting" — for cost/latency-by-agent
    input_text = db.Column(db.Text, default="")
    output_text = db.Column(db.Text, default="")
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    total_latency_ms = db.Column(db.Integer, default=0)
    retrieval_latency_ms = db.Column(db.Integer, default=0)
    retrieved_doc_ids = db.Column(db.Text, default="[]")  # JSON list
    tool_calls = db.Column(db.Text, default="[]")  # JSON list of {tool, args, duration_ms, status}
    error_status = db.Column(db.String(120), default="")
    final_outcome = db.Column(db.String(30), default="success")  # success | failure | partial
    estimated_cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    steps = db.relationship("TraceStep", backref="trace", lazy=True,
                             cascade="all, delete-orphan", order_by="TraceStep.seq")

    def retrieved_docs_list(self):
        try:
            return json.loads(self.retrieved_doc_ids or "[]")
        except json.JSONDecodeError:
            return []

    def tool_calls_list(self):
        try:
            return json.loads(self.tool_calls or "[]")
        except json.JSONDecodeError:
            return []

    def to_dict(self):
        return {
            "trace_id": self.trace_id, "model": self.model, "prompt_version": self.prompt_version,
            "request_type": self.request_type, "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens, "total_latency_ms": self.total_latency_ms,
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "retrieved_doc_ids": self.retrieved_docs_list(), "tool_calls": self.tool_calls_list(),
            "error_status": self.error_status, "final_outcome": self.final_outcome,
            "estimated_cost": self.estimated_cost, "created_at": self.created_at.isoformat(),
        }


class TraceStep(db.Model):
    """One pipeline stage within a Trace (retrieval, model call, tool call, guardrail...)."""

    __tablename__ = "trace_steps"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.Integer, db.ForeignKey("traces.id"), nullable=False, index=True)
    seq = db.Column(db.Integer, default=0)
    step_type = db.Column(db.String(40), nullable=False)  # guardrail_input | retrieval | model_call | tool_call | guardrail_output
    name = db.Column(db.String(120), default="")
    status = db.Column(db.String(20), default="ok")  # ok | failed | retried | skipped
    duration_ms = db.Column(db.Integer, default=0)
    metadata_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def metadata_dict(self):
        try:
            return json.loads(self.metadata_json or "{}")
        except json.JSONDecodeError:
            return {}


class GuardrailEvent(db.Model):
    """Every guardrail trigger (input or output), for the security dashboard."""

    __tablename__ = "guardrail_events"

    id = db.Column(db.Integer, primary_key=True)
    trace_id = db.Column(db.String(36), nullable=True, index=True)
    direction = db.Column(db.String(10), default="input")  # input | output
    rule = db.Column(db.String(80), nullable=False)  # e.g. prompt_injection, empty_input, unauthorized_action
    severity = db.Column(db.String(10), default="medium")  # low | medium | high | critical
    blocked = db.Column(db.Boolean, default=True)
    detail = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class EvalRun(db.Model):
    """One execution of the evaluation suite (a 'run' of evaluation/runner.py)."""

    __tablename__ = "eval_runs"

    id = db.Column(db.Integer, primary_key=True)
    run_label = db.Column(db.String(80), nullable=False)  # e.g. "baseline_v1", "agent-system-v2"
    prompt_version = db.Column(db.String(20), default="")
    model = db.Column(db.String(80), default="")
    total_cases = db.Column(db.Integer, default=0)
    passed_cases = db.Column(db.Integer, default=0)
    task_success_rate = db.Column(db.Float, default=0.0)
    avg_judge_score = db.Column(db.Float, default=0.0)
    tool_selection_accuracy = db.Column(db.Float, default=0.0)
    avg_latency_ms = db.Column(db.Float, default=0.0)
    p95_latency_ms = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)
    results_json_path = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns
                if c.name != "created_at"} | {"created_at": self.created_at.isoformat()}
