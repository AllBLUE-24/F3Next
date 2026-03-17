# containers/ERPNext/migration/knowledge_base.py
from typing import Dict, List, Optional

class MigrationKnowledgeBase:
    """
    Acts as the source of truth for known legacy schemas to reduce LLM hallucinations.
    In production, fetch this from Postgres.
    """
    
    def __init__(self):
        # Hardcoded for Dev/Test - move to DB later
        self._tally_ledger_map = {
            "LedgerName": "customer_name",
            "OpeningBalance": "opening_balance",
            "MailingName": "customer_name",
            "Email": "email_id"
        }
        
        self._target_schemas = {
            "Item": ["item_code", "item_name", "item_group", "stock_uom", "standard_rate"],
            "Customer": ["customer_name", "customer_type", "customer_group", "territory", "email_id"],
            "Sales Invoice": ["customer", "posting_date", "item_code", "qty", "rate", "grand_total"]
        }

    def get_known_mapping(self, source_type: str) -> Dict[str, str]:
        if source_type.lower() == "tally":
            return self._tally_ledger_map
        return {}

    def get_erpnext_schema(self, doctype: str) -> List[str]:
        """Returns the valid field names for a specific ERPNext DocType."""
        return self._target_schemas.get(doctype, [])