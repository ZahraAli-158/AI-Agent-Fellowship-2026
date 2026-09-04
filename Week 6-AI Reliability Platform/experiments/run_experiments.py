"""
Automated experiments (see experiments/experiments.md for full write-up).

Runs Experiments 1, 2, 4, 5, and 6 against an offline-stub instance of the
platform (deterministic, no API cost) and prints measured results.
Experiment 3 (different live models) is documented as a manual protocol
since it needs a paid Gemini key and human quality judgment.

Usage:
    python experiments/run_experiments.py
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


class ExpConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tempfile.gettempdir(), "ai_platform_exp.db")
    GEMINI_API_KEY = ""


def section(title):
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def main():
    db_path = os.path.join(tempfile.gettempdir(), "ai_platform_exp.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    app = create_app(ExpConfig)
    client = app.test_client()
    _orig_open = client.open

    def _open_and_refresh(*a, **kw):
        resp = _orig_open(*a, **kw)
        _db.session.remove()
        return resp

    client.open = _open_and_refresh

    with app.app_context():
        client.post("/register", data={
            "username": "expuser", "email": "exp@example.com",
            "password": "password123", "confirm_password": "password123",
        }, follow_redirects=True)
        client.post("/workspaces/create", data={"name": "Experiments WS", "category": "Research"}, follow_redirects=True)
        from app.models.models import Workspace
        ws_id = Workspace.query.filter_by(name="Experiments WS").first().id

        from app.services import gemini_service, embedding_service, document_service
        from app.services.memory_service import get_relevant_memory_context

        # ================= Experiment 1: Memory Enabled vs Disabled =================
        section("Experiment 1: Memory Enabled vs Disabled")
        context_before = get_relevant_memory_context(ws_id)
        tokens_before = gemini_service.estimate_tokens(context_before)
        client.post(f"/workspaces/{ws_id}/dashboard/memory/add", data={"content": "Prefers bullet-point answers"})
        context_after = get_relevant_memory_context(ws_id)
        tokens_after = gemini_service.estimate_tokens(context_after)
        print(f"Memory context tokens (disabled/empty): {tokens_before}")
        print(f"Memory context tokens (1 pinned fact):  {tokens_after}")
        print(f"Fact present in injected context: {'Prefers bullet-point' in context_after}")

        # ================= Experiment 2: Short vs Detailed Prompt =================
        section("Experiment 2: Short Prompt vs Detailed Prompt")
        long_text = ("Artificial intelligence is transforming industries by automating tasks, "
                     "improving decision-making, and enabling new products. " * 6)
        short_result = gemini_service.chat_completion(
            system_prompt="Summarize this.", history=[], user_message=long_text,
        )
        detailed_result = gemini_service.chat_completion(
            system_prompt=(
                "Summarize the following text in no more than 60 words, preserving key facts, "
                "removing redundancy, and returning a single paragraph."
            ),
            history=[], user_message=long_text,
        )
        print(f"Short-prompt output tokens:    {short_result['output_tokens']}")
        print(f"Detailed-prompt output tokens: {detailed_result['output_tokens']}")
        print("(Offline stub echoes input, so token deltas here reflect prompt overhead, "
              "not model behavior — rerun with a live GEMINI_API_KEY for real quality deltas.)")

        # ================= Experiment 4: Small vs Large Context Window =================
        section("Experiment 4: Small vs Large Context Window")
        convo_resp = client.post(f"/workspaces/{ws_id}/chat/new", follow_redirects=False)
        convo_id = convo_resp.headers["Location"].rstrip("/").split("/")[-1]
        for i in range(20):
            client.post(f"/workspaces/{ws_id}/chat/{convo_id}/send", data={"message": f"fact number {i}"})
        from app.models.models import Conversation
        convo = Conversation.query.get(int(convo_id))
        history = [{"role": m.role, "content": m.content} for m in convo.messages]
        small_window = history[-4:]
        large_window = history[-20:]
        small_tokens = sum(gemini_service.estimate_tokens(m["content"]) for m in small_window)
        large_tokens = sum(gemini_service.estimate_tokens(m["content"]) for m in large_window)
        print(f"Small window (4 msgs) input tokens:  {small_tokens}")
        print(f"Large window (20 msgs) input tokens: {large_tokens}")
        print(f"Large window can see 'fact number 0': {any('fact number 0' in m['content'] for m in large_window)}")
        print(f"Small window can see 'fact number 0': {any('fact number 0' in m['content'] for m in small_window)}")

        # ================= Experiment 5: Conversation Length =================
        section("Experiment 5: Conversation Length (token growth)")
        convo2_resp = client.post(f"/workspaces/{ws_id}/chat/new", follow_redirects=False)
        convo2_id = convo2_resp.headers["Location"].rstrip("/").split("/")[-1]
        checkpoints = [1, 5, 10, 20]
        sent = 0
        for target in checkpoints:
            while sent < target:
                client.post(f"/workspaces/{ws_id}/chat/{convo2_id}/send", data={"message": f"turn {sent}"})
                sent += 1
            convo2 = Conversation.query.get(int(convo2_id))
            capped_history = [{"role": m.role, "content": m.content} for m in convo2.messages][-20:]
            total_tokens = sum(gemini_service.estimate_tokens(m["content"]) for m in capped_history)
            print(f"After {target:>2} turns: {len(capped_history):>2} messages in context window, "
                  f"~{total_tokens} tokens")

        # ================= Experiment 6: Chunk Size Comparison =================
        section("Experiment 6: Chunk Size Comparison")
        sample_doc = (
            "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. "
            "It is named after the engineer Gustave Eiffel, whose company designed and built the tower. "
            "Locally nicknamed 'La dame de fer', it was constructed from 1887 to 1889 as the entrance to "
            "the 1889 World's Fair. It was initially criticized by some of France's leading artists and "
            "intellectuals for its design, but it has become a global cultural icon of France and one of "
            "the most recognizable structures in the world. The tower is 330 metres tall, about the same "
            "height as an 81-storey building, and the tallest structure in Paris."
        ) * 3

        query = "How tall is the Eiffel Tower and who built it?"
        for chunk_size in [400, 800, 1500]:
            overlap = int(chunk_size * 0.15)
            raw_chunks = document_service.chunk_text(sample_doc, chunk_size=chunk_size, overlap=overlap)

            class FakeChunk:
                def __init__(self, idx, content):
                    self.id = idx
                    self.document_id = 1
                    self.chunk_index = idx
                    self.content = content
                    self._embedding = None

                def get_embedding(self):
                    return None

            fake_chunks = [FakeChunk(i, c) for i, c in enumerate(raw_chunks)]
            results = embedding_service.semantic_search(query, fake_chunks, top_k=1)
            top_score = round(results[0]["score"], 3) if results else 0.0
            print(f"chunk_size={chunk_size:>5} -> {len(raw_chunks):>2} chunks, "
                  f"top relevance score for top-1 result: {top_score}")

    print("\n" + "=" * 60)
    print("Experiments complete. See experiments/experiments.md for full analysis.")
    print("=" * 60)

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    main()
