"""
Signals Agent — Temporal activities for F3iche inference and verification.
Moved from: backend/app/services/implementation/signals_inference.py
              backend/app/services/implementation/f3iche_verification.py
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from temporalio import activity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


# ── Embedded service logic ────────────────────────────────────────────────────

class _SignalsInferenceService:
    def __init__(self):
        self._registry: Optional[Dict] = None

    def _load_registry(self) -> Dict:
        if self._registry is None:
            path = KNOWLEDGE_DIR / "signals_registry.json"
            with open(path, "r", encoding="utf-8") as f:
                self._registry = json.load(f)
        return self._registry

    def extract_signals_from_text(self, text: str) -> List[str]:
        text_lower = text.lower()
        signals: List[str] = []
        registry = self._load_registry()
        for _, config in registry.get("signals", {}).items():
            for kw in config.get("keywords", []) + config.get("file_patterns", []) + config.get("structure_signals", []):
                if kw.lower() in text_lower:
                    signals.append(kw)
        return list(set(signals))

    def extract_signals_from_filename(self, filename: str) -> List[str]:
        name_lower = filename.lower().replace("_", " ").replace("-", " ")
        signals: List[str] = []
        registry = self._load_registry()
        for _, config in registry.get("signals", {}).items():
            for token in config.get("file_patterns", []) + config.get("keywords", []):
                if token.lower() in name_lower:
                    signals.append(token)
        return list(set(signals))

    def score_f3iche(self, f3iche_id: str, signals: List[str]) -> float:
        registry = self._load_registry()
        config = registry.get("signals", {}).get(f3iche_id, {})
        sc = registry.get("scoring", {})
        kw_w, fp_w, ss_w = sc.get("keyword_match_weight", 2), sc.get("file_pattern_weight", 3), sc.get("structure_signal_weight", 4)
        exclude_penalty, boost_mult = sc.get("exclude_penalty", -5), sc.get("boost_multiplier", 1.5)
        sl = [s.lower() for s in signals]
        score = 0.0
        for ex in config.get("exclude_keywords", []):
            if ex.lower() in sl:
                score += exclude_penalty
        for kw in config.get("keywords", []):
            if kw.lower() in sl:
                score += kw_w
        for fp in config.get("file_patterns", []):
            if fp.lower() in sl:
                score += fp_w
        for ss in config.get("structure_signals", []):
            if ss.lower() in sl:
                score += ss_w
        for bkw in config.get("boost_keywords", []):
            if bkw.lower() in sl:
                score *= boost_mult
                break
        return max(0.0, score)

    def infer_f3iche(
        self,
        uploaded_files: List[Dict],
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, float, List[str]]:
        registry = self._load_registry()
        min_threshold = registry.get("scoring", {}).get("min_confidence_threshold", 0.3)
        all_signals: List[str] = []
        for f in uploaded_files:
            name = f.get("file_name", f.get("name", ""))
            all_signals.extend(self.extract_signals_from_filename(name))
            if file_contents and name in file_contents:
                all_signals.extend(self.extract_signals_from_text(file_contents[name]))
        all_signals = list(set(all_signals))
        scores = {}
        for fid in registry.get("signals", {}).keys():
            raw = self.score_f3iche(fid, all_signals)
            scores[fid] = min(1.0, raw / 50.0)
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] < min_threshold:
            return ("trading", best[1], all_signals)
        return (best[0], best[1], all_signals)


class _F3icheVerificationService:
    NORMALIZE_MAP = {
        "trading":       ["trading", "trade", "distributor", "trader"],
        "manufacturing": ["manufacturing", "manufacture", "production", "maker"],
        "service":       ["service", "services", "consulting"],
    }

    @classmethod
    def normalize(cls, f3iche: str) -> str:
        if not f3iche:
            return ""
        f = f3iche.lower().strip()
        for canonical, aliases in cls.NORMALIZE_MAP.items():
            if f == canonical or f in aliases:
                return canonical
        return f

    @classmethod
    def verify(cls, f3iche_user: str, f3iche_signals: str, confidence: float = 0.0) -> Tuple[bool, str, Optional[str]]:
        u, s = cls.normalize(f3iche_user), cls.normalize(f3iche_signals)
        if not u:
            return (False, "pending_clarification", "Please confirm your business type from the discovery chat.")
        if not s:
            return (True, "matched", None)
        if u == s:
            return (True, "matched", None)
        msg = (
            f"Our analysis suggests you might be a **{s}** business, "
            f"but you indicated **{u}**. Could you clarify which best describes your operations?"
        )
        return (False, "mismatch", msg)


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class InferF3icheInput:
    uploaded_files: List[Dict]
    file_contents: Optional[Dict[str, str]] = None


@dataclass
class VerifyF3icheInput:
    f3iche_user: str
    f3iche_signals: str
    confidence: float = 0.0


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="infer_f3iche")
async def infer_f3iche(inp: InferF3icheInput) -> Dict:
    """Infer F3iche from uploaded file names and content signals."""
    svc = _SignalsInferenceService()
    f3iche_id, confidence, signals = svc.infer_f3iche(inp.uploaded_files, inp.file_contents)
    return {
        "f3iche": f3iche_id,
        "confidence": round(confidence, 2),
        "collected_signals": signals,
    }


@activity.defn(name="verify_f3iche")
async def verify_f3iche(inp: VerifyF3icheInput) -> Dict:
    """Verify user-stated F3iche against signals-inferred F3iche."""
    svc = _F3icheVerificationService()
    is_match, status, msg = svc.verify(inp.f3iche_user, inp.f3iche_signals, inp.confidence)
    return {
        "is_match": is_match,
        "status": status,
        "clarification_message": msg,
    }