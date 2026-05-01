import asyncio
from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional
from google.genai import types as gt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from llm_router import api_keys

class _Item(BaseModel):
    item_code: str
    qty: float
    uom: Optional[str] = None
    rate: Optional[float] = None
    warehouse: Optional[str] = None

class _Entities(BaseModel):
    customer:        Optional[str]        = None
    supplier:        Optional[str]        = None
    items:           List[_Item]          = []
    transaction_date: Optional[str]       = None

class _IntentSchema(BaseModel):
    intent_id:            str
    action:               str
    target_doctype:       str
    confidence:           float         = 0.9
    risk_level:           str           = "low"
    requires_confirmation: bool         = False
    has_ambiguities:      bool          = False
    ambiguities:          List[str]     = []
    entities:             _Entities     = Field(default_factory=_Entities)

async def main():
    client = genai.Client(api_key=api_keys[0])
    resp = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="I want to create a sales order for guruji with 5 kg of mango pickle.",
        config=gt.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_IntentSchema,
        )
    )
    print("Parsed:", resp.parsed)
    print("Text:", resp.text)
    if resp.parsed:
        print("Model dump:", resp.parsed.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
