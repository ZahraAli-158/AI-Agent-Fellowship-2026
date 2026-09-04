"""
Thin wrapper around Google's Gemini API (chat + embeddings).

Design goals:
  * Never crash the app if GEMINI_API_KEY is missing/invalid — fall back to a
    clearly-labelled offline stub so the rest of the platform (workspaces,
    memory, prompt library, dashboard, etc.) stays fully testable without a key.
  * Centralize token estimation for the cost/usage dashboard.
"""
import time
import logging

import google.generativeai as genai

logger = logging.getLogger("ai_platform.gemini")

_configured = False
_api_key = None


def configure(api_key: str):
    global _configured, _api_key
    _api_key = api_key
    if api_key:
        try:
            genai.configure(api_key=api_key)
            _configured = True
        except Exception as exc:  # pragma: no cover
            logger.warning("Gemini configuration failed: %s", exc)
            _configured = False
    else:
        _configured = False


def is_configured() -> bool:
    return _configured


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — avoids a hard dependency on a
    model-specific tokenizer while still giving a usable dashboard metric."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def chat_completion(system_prompt, history, user_message, model="gemini-3.6-flash",
                     temperature=0.7, max_tokens=1024):
    """
    Returns dict: {text, input_tokens, output_tokens, latency_ms, model_used}
    `history` is a list of {"role": "user"|"assistant", "content": str}
    """
    start = time.time()
    input_text_for_estimate = system_prompt + "\n" + "\n".join(
        m["content"] for m in history
    ) + "\n" + user_message

    if not _configured:
        latency_ms = int((time.time() - start) * 1000)
        stub = (
            "[Offline mode] No GEMINI_API_KEY is configured, so this is a simulated "
            "response. Add your Gemini API key to the .env file to get real answers.\n\n"
            f"You said: {user_message}"
        )
        return {
            "text": stub,
            "input_tokens": estimate_tokens(input_text_for_estimate),
            "output_tokens": estimate_tokens(stub),
            "latency_ms": latency_ms,
            "model_used": "offline-stub",
        }

    try:
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        # Convert history into Gemini's chat format
        gemini_history = []
        for m in history:
            role = "user" if m["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [m["content"]]})

        chat = gemini_model.start_chat(history=gemini_history)
        response = chat.send_message(user_message)
        text = response.text if hasattr(response, "text") else str(response)
        latency_ms = int((time.time() - start) * 1000)

        return {
            "text": text,
            "input_tokens": estimate_tokens(input_text_for_estimate),
            "output_tokens": estimate_tokens(text),
            "latency_ms": latency_ms,
            "model_used": model,
        }
    except Exception as exc:
        logger.error("Gemini chat_completion error: %s", exc)
        latency_ms = int((time.time() - start) * 1000)
        error_text = f"[Error contacting Gemini API: {exc}]"
        return {
            "text": error_text,
            "input_tokens": estimate_tokens(input_text_for_estimate),
            "output_tokens": 0,
            "latency_ms": latency_ms,
            "model_used": model,
            "error": True,
        }


def embed_text(text, model="models/gemini-embedding-001"):
    """Returns a list[float] embedding, or None if unavailable (caller should
    fall back to the TF-IDF search path in embedding_service.py)."""
    if not _configured or not text.strip():
        return None
    try:
        result = genai.embed_content(model=model, content=text)
        return result.get("embedding")
    except Exception as exc:
        logger.warning("Gemini embed_text error: %s", exc)
        return None


def summarize(text, model="gemini-3.6-flash", max_words=120):
    prompt = (
        f"Summarize the following text in no more than {max_words} words, "
        f"capturing the key points clearly:\n\n{text[:6000]}"
    )
    result = chat_completion(
        system_prompt="You are a precise, factual summarization engine.",
        history=[],
        user_message=prompt,
        model=model,
    )
    return result["text"]
