from pydantic import BaseModel, Field
from typing import List, Optional
import json

class _ItemWithDefaults(BaseModel):
    item_code: str
    qty: float
    uom: Optional[str] = None

class _ItemWithoutDefaults(BaseModel):
    item_code: str
    qty: float
    uom: Optional[str]

print("With Defaults:")
print(json.dumps(_ItemWithDefaults.model_json_schema(), indent=2))
print("\nWithout Defaults:")
print(json.dumps(_ItemWithoutDefaults.model_json_schema(), indent=2))
