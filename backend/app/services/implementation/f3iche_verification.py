"""F3iche match verification — user vs signals inference."""
from typing import Tuple, Optional


class F3icheVerificationService:
    """Compares user-provided F3iche with system-inferred F3iche."""

    NORMALIZE_MAP = {
        "trading": ["trading", "trade", "distributor", "trader"],
        "manufacturing": ["manufacturing", "manufacture", "production", "maker"],
        "service": ["service", "services", "consulting"],
    }

    @classmethod
    def normalize(cls, f3iche: str) -> str:
        """Normalize F3iche string for comparison."""
        if not f3iche:
            return ""
        f = f3iche.lower().strip()
        for canonical, aliases in cls.NORMALIZE_MAP.items():
            if f == canonical or f in aliases:
                return canonical
        return f

    @classmethod
    def verify(
        cls,
        f3iche_user: str,
        f3iche_signals: str,
        confidence: float = 0.0,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Verify if user and signals F3iche match.
        Returns (is_match, status, clarification_message).
        - is_match: True if same, False if mismatch
        - status: matched | mismatch | pending_clarification
        - clarification_message: Message to show user if mismatch
        """
        u = cls.normalize(f3iche_user)
        s = cls.normalize(f3iche_signals)

        if not u:
            return (False, "pending_clarification", "Please confirm your business type from the discovery chat.")

        if not s:
            return (True, "matched", None)  # No signals yet, trust user

        if u == s:
            return (True, "matched", None)

        # Mismatch
        msg = (
            f"Our analysis of your uploaded files suggests you might be a **{s}** business, "
            f"but you indicated **{u}**. Could you clarify which best describes your operations?"
        )
        return (False, "mismatch", msg)
