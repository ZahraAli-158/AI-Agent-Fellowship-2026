"""
Input guardrails (Week 6, Requirement 12) + prompt-injection detection
(Requirement 13/26).

These are deliberately conservative heuristics, not a claim of perfect
detection — the report (docs/WEEK6_SECURITY_REVIEW.md) discusses their
limitations. The goal per §12 is to catch clearly bad input without
unnecessarily blocking normal requests, and to log every trigger.
"""
import re

from app.models.models import db, GuardrailEvent

MAX_INPUT_CHARS = 8000

# Requests for actions/capabilities this platform does not have. Distinct
# from prompt injection (which tries to override behavior) — these are
# requests for something the assistant was never able to do in the first
# place, and should be told so plainly rather than attempted or silently
# ignored (Week 6 §24 "Unsupported operations").
UNSUPPORTED_OPERATION_PATTERNS = [
    (r"\bbrowse (the )?(internet|web)\b", "web_browsing"),
    (r"\bmake a (phone call|call)\b", "phone_call"),
    (r"\baccess (my )?(bank account|credit card|payment)\b", "financial_account_access"),
    (r"\b(run|execute) (this )?(shell|bash|python|arbitrary) (command|code|script)\b", "arbitrary_code_execution"),
    (r"\binstall (a |an )?(package|program|software)\b.{0,20}\bon (my|your|the) (computer|server|machine)\b",
     "software_installation"),
    (r"\bsend (a )?(sms|text message) to\b", "sms_sending"),
    (r"\baccess (the )?(camera|microphone|gps|location) (of|on) (my|this) device\b", "device_hardware_access"),
]
_UNSUPPORTED_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in UNSUPPORTED_OPERATION_PATTERNS]

# Patterns aimed at *direct* prompt injection / instruction override attempts.
INJECTION_PATTERNS = [
    (r"\bignore (all|any|the) (previous|prior|above)\b.{0,30}(instructions?|prompt)", "override_instructions"),
    (r"\bdisregard (all|any|the)? ?(previous|prior|above|system)\b", "override_instructions"),
    (r"\byou are now\b", "role_override"),
    (r"\bact as (?:if )?(?:a|an)\b.{0,40}\bwith no (restrictions|rules|filters)", "role_override"),
    (r"\breveal (the )?(system prompt|hidden prompt|instructions)\b", "prompt_exfiltration"),
    (r"\bwhat (is|are) your (system prompt|instructions)\b", "prompt_exfiltration"),
    (r"\b(api[_ ]?key|secret key|password)\b.{0,20}\b(reveal|show|print|leak|give me)\b", "secret_exfiltration"),
    (r"\b(reveal|show|print|leak|give me)\b.{0,20}\b(api[_ ]?key|secret key|password)\b", "secret_exfiltration"),
    (r"\bwhat (is|are)\b.{0,40}\b(api[_ ]?key|secret key|password|environment variable)\b.{0,20}"
     r"\bset to\b", "secret_exfiltration"),
    (r"\bdelete (all|every|the)\b.{0,20}\b(data|records|users|database)\b", "unauthorized_destructive_action"),
    (r"\bwithout (approval|asking|confirmation)\b", "approval_bypass"),
    (r"\bskip (the )?approval\b", "approval_bypass"),
    (r"\b(as my|i am your)\b.{0,20}\b(system administrator|admin|developer|owner)\b.{0,20}"
     r"\b(authoriz|bypass|override|grant)", "elevated_authorization_claim"),
    (r"\bbypass all\b.{0,20}\b(safety|security)\b.{0,15}\bchecks?\b", "elevated_authorization_claim"),
    (r"\brepeat everything above\b|\brepeat (all|everything)\b.{0,20}\b(above|before) this\b", "prompt_exfiltration"),
    (r"\bDAN\b|do anything now", "jailbreak_persona"),
    (r"<\s*system\s*>|\[system\]", "fake_system_block"),
    (r"\b(list|reveal|show|give me)\b.{0,25}\b(other users?'?|every user'?s?|all users?'?)\b.{0,25}"
     r"\b(email|data|workspace|password|information)\b", "workspace_data_exfiltration"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in INJECTION_PATTERNS]


class GuardrailResult:
    def __init__(self, allowed=True, blocked_reason=None, rule=None, severity="low"):
        self.allowed = allowed
        self.blocked_reason = blocked_reason
        self.rule = rule
        self.severity = severity

    def __bool__(self):
        return self.allowed


def _log_trigger(direction, rule, severity, blocked, detail, trace_id=None):
    try:
        db.session.add(GuardrailEvent(
            trace_id=trace_id, direction=direction, rule=rule, severity=severity,
            blocked=blocked, detail=(detail or "")[:500],
        ))
        db.session.commit()
    except Exception:  # pragma: no cover - never let logging break input validation
        db.session.rollback()


def detect_prompt_injection(text: str):
    """Returns (is_suspicious: bool, rule: str|None) for direct injection
    attempts inside user-authored text."""
    if not text:
        return False, None
    for pattern, label in _COMPILED:
        if pattern.search(text):
            return True, label
    return False, None


def scan_retrieved_document(text: str):
    """Indirect prompt injection (Week 6 §26): retrieved document text must
    be treated as DATA, never as instructions. This flags documents that
    contain instruction-like content so callers can strip/quarantine it
    before it reaches the model context."""
    is_suspicious, rule = detect_prompt_injection(text or "")
    if is_suspicious:
        return True, rule
    # Additional check specific to documents pretending to be system turns.
    if re.search(r"^\s*(system|assistant)\s*:", text or "", re.IGNORECASE | re.MULTILINE):
        return True, "fake_role_header"
    return False, None


def detect_unsupported_operation(text: str):
    """Returns (is_unsupported: bool, rule: str|None) for requests asking
    the assistant to do something this platform genuinely cannot do (make
    phone calls, browse the live web, execute arbitrary shell code,
    access device hardware, etc.) — distinct from prompt injection, which
    tries to override behavior rather than request a missing capability."""
    if not text:
        return False, None
    for pattern, label in _UNSUPPORTED_COMPILED:
        if pattern.search(text):
            return True, label
    return False, None


def validate_input(text: str, trace_id=None, log=True):
    """Runs all input guardrails. Returns a GuardrailResult."""
    if text is None or not text.strip():
        result = GuardrailResult(False, "Empty request.", "empty_input", "low")
        if log:
            _log_trigger("input", result.rule, result.severity, True, "empty or whitespace-only input", trace_id)
        return result

    if len(text) > MAX_INPUT_CHARS:
        result = GuardrailResult(False, f"Input exceeds {MAX_INPUT_CHARS} characters.",
                                   "input_too_long", "low")
        if log:
            _log_trigger("input", result.rule, result.severity, True, f"len={len(text)}", trace_id)
        return result

    is_suspicious, rule = detect_prompt_injection(text)
    if is_suspicious:
        result = GuardrailResult(False, "This request looks like an attempt to override system "
                                          "instructions or access unauthorized data, so it was blocked.",
                                   f"prompt_injection:{rule}", "high")
        if log:
            _log_trigger("input", result.rule, result.severity, True, text[:200], trace_id)
        return result

    is_unsupported, unsupported_rule = detect_unsupported_operation(text)
    if is_unsupported:
        result = GuardrailResult(False, "This platform can't do that — it can't browse the live web, "
                                          "make calls, execute arbitrary code, or access device hardware. "
                                          "I can help with tasks, your knowledge base, and conversation.",
                                   f"unsupported_operation:{unsupported_rule}", "low")
        if log:
            _log_trigger("input", result.rule, result.severity, True, text[:200], trace_id)
        return result

    # Malformed data: control characters / null bytes that suggest a raw
    # binary payload rather than a normal chat message.
    if any(ord(ch) < 9 for ch in text):
        result = GuardrailResult(False, "Input contains invalid control characters.",
                                   "malformed_input", "medium")
        if log:
            _log_trigger("input", result.rule, result.severity, True, "control chars detected", trace_id)
        return result

    return GuardrailResult(True)
