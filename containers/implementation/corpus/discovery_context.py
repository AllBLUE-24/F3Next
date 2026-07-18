"""Discovery context loading and validation for Step 2 corpus understanding."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class DiscoveryContextError(Exception):
    """Raised when required discovery context is missing."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class DiscoveryContextResult:
    context_block: str
    ok: bool
    source: str = "none"
    warnings: List[Dict[str, str]] = field(default_factory=list)


def _env_truthy(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in ("true", "1", "yes")


def require_discovery_context_enabled() -> bool:
    """When true, enrich fails fast without usable discovery context."""
    if _env_truthy("CORPUS_ALLOW_DEFAULTS", "false"):
        return False
    return _env_truthy("CORPUS_REQUIRE_DISCOVERY", "true")


def _has_user_transcript(chat_history: Optional[List[Dict[str, Any]]]) -> bool:
    if not chat_history:
        return False
    return any(
        isinstance(m, dict) and m.get("role") == "user" and str(m.get("content") or "").strip()
        for m in chat_history
    )


def _metadata_has_business_signal(discovery_metadata: Optional[Dict[str, Any]]) -> bool:
    if not discovery_metadata or not isinstance(discovery_metadata, dict):
        return False
    keys = (
        "f3iche", "industry", "bottleneck", "pain_point",
        "mvp_focus", "primary_bottleneck",
    )
    if any(discovery_metadata.get(k) for k in keys):
        return True
    mvp = discovery_metadata.get("mvp_focus")
    return isinstance(mvp, dict) and bool(mvp.get("primary_bottleneck"))


def build_discovery_context_block(
    chat_history: Optional[List[Dict[str, Any]]] = None,
    discovery_metadata: Optional[Dict[str, Any]] = None,
    *,
    discovery_status: Optional[str] = None,
    require: Optional[bool] = None,
) -> DiscoveryContextResult:
    """
    Build the discovery context paragraph injected into the corpus LLM prompt.

    When require=True (default from CORPUS_REQUIRE_DISCOVERY), raises DiscoveryContextError
    if neither transcript nor discovery metadata provides business signal.
    """
    if require is None:
        require = require_discovery_context_enabled()

    warnings: List[Dict[str, str]] = []
    has_transcript = _has_user_transcript(chat_history)
    has_metadata = _metadata_has_business_signal(discovery_metadata)

    if require and not has_transcript and not has_metadata:
        raise DiscoveryContextError(
            "DISCOVERY_CONTEXT_MISSING",
            "Discovery context required for corpus understanding "
            "(complete discovery chat or discovery_metadata with f3iche/bottleneck).",
        )

    if not has_transcript and not has_metadata:
        return DiscoveryContextResult(context_block="", ok=False, source="none", warnings=warnings)

    context_parts = ["BUSINESS CONTEXT FROM DISCOVERY (primary — overrides filename guesses):"]

    if discovery_status:
        context_parts.append(f"- Discovery status: {discovery_status}")

    if discovery_metadata:
        f3iche = discovery_metadata.get("f3iche")
        if f3iche:
            context_parts.append(f"- Confirmed F3iche: {f3iche}")

        industry = discovery_metadata.get("industry") or discovery_metadata.get("f3iche_industry")
        if industry:
            context_parts.append(f"- Industry/business type: {industry}")

        bottleneck = (
            discovery_metadata.get("bottleneck")
            or discovery_metadata.get("pain_point")
        )
        mvp = discovery_metadata.get("mvp_focus") if isinstance(discovery_metadata.get("mvp_focus"), dict) else {}
        if not bottleneck and isinstance(mvp, dict):
            bottleneck = mvp.get("primary_bottleneck")
        if bottleneck:
            context_parts.append(f"- User's stated bottleneck/pain point: {bottleneck}")

        scale = discovery_metadata.get("scale") or discovery_metadata.get("company_scale")
        if scale:
            context_parts.append(f"- Company scale: {scale}")

        legacy_system = discovery_metadata.get("legacy_system")
        if legacy_system:
            context_parts.append(f"- Current system: {legacy_system}")

        if isinstance(mvp, dict) and mvp.get("functional_requirements"):
            reqs = mvp.get("functional_requirements")
            if isinstance(reqs, list) and reqs:
                preview = "; ".join(str(r) for r in reqs[:5])
                context_parts.append(f"- Day-1 functional focus: {preview}")

    if has_transcript and chat_history:
        user_messages = [
            str(msg.get("content", ""))
            for msg in chat_history
            if isinstance(msg, dict) and msg.get("role") == "user"
        ]
        recent = [m for m in user_messages if m.strip()][-3:]
        if recent:
            context_parts.append("- Recent user statements:")
            for i, msg in enumerate(recent, 1):
                context_parts.append(f"  {i}. {msg[:200].strip()}")

    if len(context_parts) == 1:
        if require:
            raise DiscoveryContextError(
                "DISCOVERY_CONTEXT_EMPTY",
                "Discovery context block could not be built from provided inputs.",
            )
        return DiscoveryContextResult(context_block="", ok=False, source="partial", warnings=warnings)

    context_parts.append(
        "\nUse this discovery context as the primary lens for interpreting uploads. "
        "Filenames and column headers are secondary evidence only."
    )

    source = "discovery"
    if discovery_status and str(discovery_status).upper() != "COMPLETE":
        warnings.append({
            "code": "DISCOVERY_INCOMPLETE",
            "message": f"Discovery status is {discovery_status}; corpus understanding may be less accurate.",
        })

    return DiscoveryContextResult(
        context_block="\n".join(context_parts),
        ok=True,
        source=source,
        warnings=warnings,
    )


def extract_discovery_context(
    chat_history: Optional[List[Dict[str, Any]]] = None,
    discovery_metadata: Optional[Dict[str, Any]] = None,
    discovery_status: Optional[str] = None,
) -> str:
    """Backward-compatible string helper used by enrich and harness."""
    result = build_discovery_context_block(
        chat_history,
        discovery_metadata,
        discovery_status=discovery_status,
        require=False,
    )
    return result.context_block
