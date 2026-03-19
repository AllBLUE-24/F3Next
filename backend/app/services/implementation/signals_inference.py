"""Signals-based F3iche inference from uploaded files."""
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "implementation" / "knowledge"


class SignalsInferenceService:
    """Scans uploaded files, collects signals, scores F3iches, returns best match."""

    def __init__(self):
        self._registry = None

    def _load_registry(self) -> Dict:
        if self._registry is None:
            path = KNOWLEDGE_DIR / "signals_registry.json"
            with open(path, "r", encoding="utf-8") as f:
                self._registry = json.load(f)
        return self._registry

    def extract_signals_from_text(self, text: str) -> List[str]:
        """Extract keywords and patterns from file content."""
        text_lower = text.lower()
        signals = []
        registry = self._load_registry()
        scoring = registry.get("scoring", {})

        for f3iche_id, config in registry.get("signals", {}).items():
            for kw in config.get("keywords", []):
                if kw.lower() in text_lower:
                    signals.append(kw)
            for fp in config.get("file_patterns", []):
                if fp.lower() in text_lower:
                    signals.append(fp)
            for ss in config.get("structure_signals", []):
                if ss.lower() in text_lower:
                    signals.append(ss)

        return list(set(signals))

    def extract_signals_from_filename(self, filename: str) -> List[str]:
        """Extract signals from file name."""
        name_lower = filename.lower().replace("_", " ").replace("-", " ")
        signals = []
        registry = self._load_registry()

        for f3iche_id, config in registry.get("signals", {}).items():
            for fp in config.get("file_patterns", []):
                if fp.lower() in name_lower:
                    signals.append(fp)
            for kw in config.get("keywords", []):
                if kw.lower() in name_lower:
                    signals.append(kw)

        return list(set(signals))

    def score_f3iche(self, f3iche_id: str, signals: List[str]) -> float:
        """Score a single F3iche against collected signals."""
        registry = self._load_registry()
        config = registry.get("signals", {}).get(f3iche_id, {})
        scoring = registry.get("scoring", {})

        kw_weight = scoring.get("keyword_match_weight", 2)
        fp_weight = scoring.get("file_pattern_weight", 3)
        ss_weight = scoring.get("structure_signal_weight", 4)
        exclude_penalty = scoring.get("exclude_penalty", -5)
        boost_mult = scoring.get("boost_multiplier", 1.5)

        score = 0.0
        signals_lower = [s.lower() for s in signals]

        # Exclude penalty
        for ex in config.get("exclude_keywords", []):
            if ex.lower() in signals_lower:
                score += exclude_penalty

        # Keyword matches
        for kw in config.get("keywords", []):
            if kw.lower() in signals_lower:
                score += kw_weight

        # File pattern matches
        for fp in config.get("file_patterns", []):
            if fp.lower() in signals_lower:
                score += fp_weight

        # Structure signal matches
        for ss in config.get("structure_signals", []):
            if ss.lower() in signals_lower:
                score += ss_weight

        # Boost
        for bkw in config.get("boost_keywords", []):
            if bkw.lower() in signals_lower:
                score *= boost_mult
                break

        return max(0.0, score)

    def infer_f3iche(
        self,
        uploaded_files: List[Dict],
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, float, List[str]]:
        """
        Infer F3iche from uploaded files.
        Returns (f3iche_id, confidence, collected_signals).
        """
        registry = self._load_registry()
        all_signals = []
        min_threshold = registry.get("scoring", {}).get("min_confidence_threshold", 0.3)

        for f in uploaded_files:
            name = f.get("file_name", f.get("name", ""))
            all_signals.extend(self.extract_signals_from_filename(name))
            if file_contents and name in file_contents:
                all_signals.extend(
                    self.extract_signals_from_text(file_contents[name])
                )

        all_signals = list(set(all_signals))
        f3iche_ids = list(registry.get("signals", {}).keys())
        scores = {}

        for fid in f3iche_ids:
            raw_score = self.score_f3iche(fid, all_signals)
            total_possible = 50.0  # Approximate max
            confidence = min(1.0, raw_score / total_possible) if total_possible else 0
            scores[fid] = confidence

        best = max(scores.items(), key=lambda x: x[1])
        if best[1] < min_threshold:
            return ("trading", best[1], all_signals)  # Default fallback
        return (best[0], best[1], all_signals)
