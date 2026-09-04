"""
Automated evaluation runner.

Executes the scenarios marked [auto] in evaluation/eval_scenarios.md against
a fresh in-memory instance of the platform (offline Gemini stub, for fully
deterministic results) and prints a pass/fail report with timing stats.

Usage:
    python evaluation/eval_runner.py
"""
import io
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models.models import db as _db
from config import Config


class EvalConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tempfile.gettempdir(), "ai_platform_eval.db")
    GEMINI_API_KEY = ""


RESULTS = []


def check(name, condition, latency_ms=None):
    RESULTS.append({"name": name, "passed": bool(condition), "latency_ms": latency_ms})
    status = "PASS" if condition else "FAIL"
    extra = f" ({latency_ms}ms)" if latency_ms is not None else ""
    print(f"[{status}] {name}{extra}")


def timed(fn):
    start = time.time()
    result = fn()
    return result, int((time.time() - start) * 1000)


def run():
    db_path = os.path.join(tempfile.gettempdir(), "ai_platform_eval.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    app = create_app(EvalConfig)
    client = app.test_client()

    # SQLite read-snapshot fix: the outer app_context's db.session can hold a
    # stale transaction snapshot from earlier ORM reads, so writes committed
    # by the test client's per-request sessions may not become visible. We
    # force the session to reset after every request so subsequent queries
    # always see the latest committed state.
    _orig_open = client.open

    def _open_and_refresh(*a, **kw):
        resp = _orig_open(*a, **kw)
        _db.session.remove()
        return resp

    client.open = _open_and_refresh

    def register(username, email):
        return client.post("/register", data={
            "username": username, "email": email,
            "password": "password123", "confirm_password": "password123",
        }, follow_redirects=True)

    def create_ws(name):
        client.post("/workspaces/create", data={"name": name, "category": "Custom"}, follow_redirects=True)
        from app.models.models import Workspace
        return Workspace.query.filter_by(name=name).first()

    with app.app_context():
        register("evaluser", "eval@example.com")
        ws = create_ws("Eval Workspace")
        ws_id = ws.id

        # --- Scenario 6: empty message rejected ---
        convo_resp = client.post(f"/workspaces/{ws_id}/chat/new", follow_redirects=False)
        convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]
        resp, ms = timed(lambda: client.post(f"/workspaces/{ws_id}/chat/{convo_id}/send", data={"message": ""}))
        check("Scenario 6: empty message rejected", resp.status_code == 400, ms)

        # --- Scenario 7 & 8: upload + citation + summary ---
        sample = (b"The Eiffel Tower is in Paris. It was completed in 1889 by Gustave Eiffel's company "
                  b"for the World's Fair and remains a global icon of France.")
        resp, ms = timed(lambda: client.post(
            f"/workspaces/{ws_id}/knowledge/upload",
            data={"document": (io.BytesIO(sample), "eiffel.txt")},
            content_type="multipart/form-data", follow_redirects=True,
        ))
        from app.models.models import Document
        doc = Document.query.filter_by(workspace_id=ws_id, filename="eiffel.txt").first()
        doc_id = doc.id
        check("Scenario 7: document uploaded and chunked", doc is not None and len(doc.chunks) >= 1, ms)
        check("Scenario 8: summary generated at upload time", bool(doc.summary), ms)

        # --- Scenario 9-ish / knowledge search relevance ---
        resp, ms = timed(lambda: client.get(f"/workspaces/{ws_id}/knowledge/search?q=Eiffel Tower Paris"))
        results = resp.get_json()["results"]
        check("Scenario 10: semantic search returns relevant top result", bool(results) and "eiffel" in results[0]["document"], ms)

        # --- Scenario 11: knowledge toggle off means no citations ---
        resp, ms = timed(lambda: client.post(
            f"/workspaces/{ws_id}/chat/{convo_id}/send", data={"message": "Tell me about the Eiffel Tower"}
        ))
        no_kb_citations = resp.get_json()["assistant_message"]["citations"]
        check("Scenario 11: no citations when knowledge base unchecked", no_kb_citations == [], ms)

        # --- with KB on ---
        resp, ms = timed(lambda: client.post(
            f"/workspaces/{ws_id}/chat/{convo_id}/send",
            data={"message": "Tell me about the Eiffel Tower", "use_knowledge": "on"},
        ))
        with_kb_citations = resp.get_json()["assistant_message"]["citations"]
        check("Citation quality: citations present when KB enabled", len(with_kb_citations) > 0, ms)

        # --- Scenario 12: delete document -> citations gone ---
        client.post(f"/workspaces/{ws_id}/knowledge/{doc_id}/delete", follow_redirects=True)
        resp, ms = timed(lambda: client.post(
            f"/workspaces/{ws_id}/chat/{convo_id}/send",
            data={"message": "Tell me about the Eiffel Tower", "use_knowledge": "on"},
        ))
        check("Scenario 12: citations removed after document deletion",
              resp.get_json()["assistant_message"]["citations"] == [], ms)

        # --- Scenario 13: memory recall across new conversation ---
        client.post(f"/workspaces/{ws_id}/chat/{convo_id}/send", data={"message": "I like concise answers"})
        new_convo_resp = client.post(f"/workspaces/{ws_id}/chat/new", follow_redirects=False)
        new_convo_id = new_convo_resp.headers["Location"].rstrip("/").split("/")[-1]
        from app.services.memory_service import get_relevant_memory_context
        context, ms = timed(lambda: get_relevant_memory_context(ws_id))
        check("Scenario 13: memory recall across sessions", "concise" in context, ms)

        # --- Scenario 14: manual pin appears in context ---
        client.post(f"/workspaces/{ws_id}/dashboard/memory/add", data={"content": "Favorite color is teal"})
        context2 = get_relevant_memory_context(ws_id)
        check("Scenario 14: pinned memory appears in context", "teal" in context2)

        # --- Scenario 16: delete memory removes from context ---
        from app.models.models import MemoryItem
        item = MemoryItem.query.filter_by(workspace_id=ws_id, content="Favorite color is teal").first()
        client.post(f"/workspaces/{ws_id}/dashboard/memory/{item.id}/delete")
        context3 = get_relevant_memory_context(ws_id)
        check("Scenario 16: deleted memory absent from context", "teal" not in context3)

        # --- Scenario 18: memory isolation across workspaces ---
        ws2 = create_ws("Eval Workspace 2")
        ws2_id = ws2.id
        context_ws2 = get_relevant_memory_context(ws2_id)
        check("Scenario 18: memory isolated per workspace", "concise" not in context_ws2)

        # --- Scenario 19: message ordering ---
        for i in range(5):
            client.post(f"/workspaces/{ws_id}/chat/{new_convo_id}/send", data={"message": f"message {i}"})
        from app.models.models import Conversation
        convo = Conversation.query.get(int(new_convo_id))
        texts = [m.content for m in convo.messages if m.role == "user"]
        check("Scenario 19: message order preserved", texts == [f"message {i}" for i in range(5)])

        # --- Scenario 21: rename persists ---
        client.post(f"/workspaces/{ws_id}/chat/{new_convo_id}/rename", data={"title": "Renamed"}, follow_redirects=True)
        check("Scenario 21: conversation rename persists", Conversation.query.get(int(new_convo_id)).title == "Renamed")

        # --- Scenario 22: pin sorts to top ---
        client.post(f"/workspaces/{ws_id}/chat/{new_convo_id}/pin")
        list_resp = client.get(f"/workspaces/{ws_id}")
        check("Scenario 22: pin toggled successfully", Conversation.query.get(int(new_convo_id)).is_pinned is True)

        # --- Scenario 23: export ---
        resp, ms = timed(lambda: client.get(f"/workspaces/{ws_id}/chat/{new_convo_id}/export?format=markdown"))
        check("Scenario 23: markdown export succeeds", resp.status_code == 200 and b"message 0" in resp.data, ms)
        resp, ms = timed(lambda: client.get(f"/workspaces/{ws_id}/chat/{new_convo_id}/export?format=pdf"))
        check("Scenario 23: pdf export succeeds", resp.status_code == 200, ms)

        # --- Scenario 24: cascade delete ---
        msg_count_before = len(Conversation.query.get(int(new_convo_id)).messages)
        client.post(f"/workspaces/{ws_id}/chat/{new_convo_id}/delete", follow_redirects=True)
        check("Scenario 24: conversation cascade delete", Conversation.query.get(int(new_convo_id)) is None
              and msg_count_before > 0)

        # --- Scenario 25-27: prompt templates ---
        client.post(f"/workspaces/{ws_id}/prompts/create", data={"title": "T1", "category": "Writing", "content": "c1"})
        from app.models.models import PromptTemplate
        tpl = PromptTemplate.query.filter_by(title="T1").first()
        tpl_id = tpl.id
        check("Scenario 25: template created", tpl is not None)
        client.post(f"/workspaces/{ws_id}/prompts/{tpl_id}/edit", data={"title": "T1 edited", "category": "Writing", "content": "c2"})
        check("Scenario 26: template edit persists", PromptTemplate.query.get(tpl_id).title == "T1 edited")
        client.post(f"/workspaces/{ws_id}/prompts/{tpl_id}/use")
        check("Scenario 27: use_count increments", PromptTemplate.query.get(tpl_id).use_count == 1)

        # --- Scenario 33-35: skills ---
        from app.models.models import Skill, SkillExecution
        skill = Skill.query.filter_by(key="summarization").first()
        skill_id = skill.id
        resp, ms = timed(lambda: client.post(f"/workspaces/{ws_id}/skills/{skill_id}/run", data={"input_text": ""}))
        check("Scenario 33: skill run rejects empty input", resp.status_code == 400, ms)
        resp, ms = timed(lambda: client.post(f"/workspaces/{ws_id}/skills/{skill_id}/run", data={"input_text": "hello world"}))
        check("Scenario 34/35: skill executes and logs (offline stub)", resp.status_code == 200, ms)
        exec_count = SkillExecution.query.filter_by(workspace_id=ws_id, skill_id=skill_id).count()
        check("Scenario 34: execution logged", exec_count == 1)

        # --- Scenario 29: cross-user prompt delete rejected ---
        client.get("/logout")
        register("evaluser2", "eval2@example.com")
        resp = client.post(f"/workspaces/{ws_id}/prompts/{tpl_id}/delete", follow_redirects=True)
        check("Scenario 29: cross-user prompt delete has no effect", PromptTemplate.query.get(tpl_id) is not None)

        # --- Scenario 38: cross-user workspace access forbidden ---
        resp = client.get(f"/workspaces/{ws_id}")
        check("Scenario 38: cross-user workspace access forbidden", resp.status_code == 403)

        # --- Scenario 37: unsupported file type rejected (back as the owner) ---
        client.get("/logout")
        client.post("/login", data={"identifier": "evaluser", "password": "password123"})
        resp = client.post(
            f"/workspaces/{ws_id}/knowledge/upload",
            data={"document": (io.BytesIO(b"x"), "bad.exe")},
            content_type="multipart/form-data", follow_redirects=True,
        )
        check("Scenario 37: unsupported file type rejected", b"Unsupported file type" in resp.data)

        # --- Scenario 39: temperature clamped ---
        client.post(f"/workspaces/{ws_id}/settings", data={
            "assistant_name": "X", "assistant_role": "Y", "system_prompt": "Z",
            "model": "gemini-3.6-flash", "personality": "P", "response_style": "S",
            "temperature": "99", "max_tokens": "512",
        })
        from app.models.models import Workspace
        check("Scenario 39: temperature clamped to valid range", Workspace.query.get(ws_id).temperature <= 2.0)

        # --- Scenario 40: duplicate email rejected (case-insensitive) ---
        client.get("/logout")
        resp = client.post("/register", data={
            "username": "newname", "email": "EVAL@example.com",
            "password": "password123", "confirm_password": "password123",
        })
        check("Scenario 40: duplicate email (case-insensitive) rejected", b"already registered" in resp.data)

    # ---- Report ----
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    latencies = [r["latency_ms"] for r in RESULTS if r["latency_ms"] is not None]
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0

    print("\n" + "=" * 60)
    print(f"EVALUATION SUMMARY: {passed}/{total} scenarios passed ({round(100*passed/total,1)}%)")
    print(f"Average measured latency: {avg_latency}ms across {len(latencies)} timed calls")
    print("=" * 60)

    if os.path.exists(db_path):
        os.remove(db_path)

    return passed == total


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
