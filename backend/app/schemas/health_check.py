from pydantic import BaseModel
from typing import Dict, Any

class HealthCheckPayload(BaseModel):
    firebase_uid: str
    user_email: str
    
    # --- NEW FIELDS ---
    full_name: str
    role: str 
    
    company_name: str
    answers: Dict[str, Any]