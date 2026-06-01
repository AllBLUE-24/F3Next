"""Map pipeline step names to IS chat UI steps."""

from __future__ import annotations


def step_to_chat_step(step_name: str, pipeline: str = "IS") -> str:
    if pipeline != "IS":
        return "analyze"
    name = (step_name or "").lower()
    if "validate" in name:
        return "validate"
    if "import" in name or "execute_import" in name or "preflight" in name:
        return "import"
    if "finalize" in name or "import_plan" in name:
        return "validate"
    if "map" in name or "classify" in name or "corpus" in name:
        return "analyze"
    return "analyze"
