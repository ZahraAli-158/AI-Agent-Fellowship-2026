"""Prompt versioning registry (Week 6, Requirement 10).

Loads prompts/v*.txt + metadata.json so the evaluation runner can execute
the same dataset against every version and compare results (Requirement 22).
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_metadata():
    with open(os.path.join(_HERE, "metadata.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def update_evaluation_score(version: str, score: float, if_version=None):
    """Writes a version's measured task_success_rate (0-1) back into
    metadata.json's evaluation_score field (Week 6 §21 — "Store: ...
    Evaluation score"). Called by evaluation/runner.py after a run whose
    label maps to a known prompt version."""
    path = os.path.join(_HERE, "metadata.json")
    data = load_metadata()
    updated = False
    for v in data["versions"]:
        if v["version"] == version:
            v["evaluation_score"] = round(score, 4)
            updated = True
    if updated:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return updated


def load_prompt_text(version: str) -> str:
    path = os.path.join(_HERE, f"{version}.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def all_versions():
    return [v["version"] for v in load_metadata()["versions"]]


def render(version: str, **kwargs) -> str:
    template = load_prompt_text(version)
    defaults = {
        "assistant_name": "Assistant", "assistant_role": "A helpful general-purpose assistant",
        "personality": "Friendly and professional", "response_style": "Balanced",
    }
    defaults.update(kwargs)
    try:
        return template.format(**defaults)
    except KeyError:
        return template
