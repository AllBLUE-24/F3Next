"""Company Profile & Context — versioned, updated after every action."""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Knowledge base path
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "implementation" / "knowledge"


class CompanyProfileService:
    """Manages versioned company profile and context."""

    @staticmethod
    def _load_f3iche(f3iche_id: str) -> Optional[Dict]:
        path = KNOWLEDGE_DIR / f"f3iche_{f3iche_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _load_doctypes_graph() -> Dict:
        path = KNOWLEDGE_DIR / "doctypes_graph_ERPNext.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def build_profile(
        cls,
        project_id: str,
        version: int,
        f3iche: str,
        industry: str,
        industry_sub: Optional[str] = None,
        company_size: Optional[str] = None,
        company_name: Optional[str] = None,
        f3iche_user: Optional[str] = None,
        f3iche_signals: Optional[str] = None,
        f3iche_match_status: str = "matched",
        uploaded_files: Optional[List[Dict]] = None,
        collected_signals: Optional[List[str]] = None,
        target_structure: Optional[Dict] = None,
        field_mappings: Optional[Dict] = None,
        validation_report: Optional[Dict] = None,
        import_phase: Optional[str] = None,
        action: str = "create",
    ) -> Dict[str, Any]:
        """Build full company profile snapshot."""
        f3iche_data = cls._load_f3iche(f3iche)
        if not f3iche_data:
            workflows = []
            modules = []
            required_doctypes = []
        else:
            workflows = [w.get("name", "") for w in f3iche_data.get("workflows", [])]
            modules = f3iche_data.get("required_modules", [])
            required_doctypes = f3iche_data.get("required_doctypes", [])

        return {
            "project_id": project_id,
            "version": version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "f3iche": f3iche,
            "industry": industry,
            "industry_sub": industry_sub,
            "company_size": company_size,
            "company_name": company_name,
            "workflows": workflows,
            "modules": modules,
            "required_doctypes": required_doctypes,
            "f3iche_user": f3iche_user,
            "f3iche_signals": f3iche_signals,
            "f3iche_match_status": f3iche_match_status,
            "uploaded_files": uploaded_files or [],
            "collected_signals": collected_signals or [],
            "target_structure": target_structure,
            "field_mappings": field_mappings,
            "validation_report": validation_report,
            "import_phase": import_phase,
        }

    @classmethod
    def get_latest_context(cls, profile: Dict) -> Dict[str, Any]:
        """Extract latest context for downstream agents."""
        return {
            "f3iche": profile.get("f3iche"),
            "industry": profile.get("industry"),
            "modules": profile.get("modules", []),
            "required_doctypes": profile.get("required_doctypes", []),
            "target_structure": profile.get("target_structure"),
            "field_mappings": profile.get("field_mappings"),
        }
