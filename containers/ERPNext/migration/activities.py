# containers/erpnext_inventory/migration/activities.py
import os
import json
import boto3
import pandas as pd
import io
import aiohttp
import asyncio
from temporalio import activity
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# Local imports
from .knowledge_base import MigrationKnowledgeBase
from .prompts import SYSTEM_PROMPT_ANALYZER, USER_PROMPT_TEMPLATE

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# --- CONFIGURATION ---
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# Initialize AWS S3 & KB
kb = MigrationKnowledgeBase()
s3 = boto3.client("s3")

@activity.defn
async def download_and_extract_schema(s3_key: str) -> Dict[str, Any]:
    """
    Downloads file from S3, reads headers and sample rows.
    Returns metadata for the AI.
    """
    try:
        activity.logger.info(f"Downloading file: {s3_key}")
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_content = response['Body'].read()
        
        # Determine loader based on extension
        if s3_key.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(file_content))
        elif s3_key.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        else:
            raise ValueError("Unsupported file format. Please upload Excel or CSV.")

        # Extract context
        headers = list(df.columns)
        # Convert first 3 rows to string for AI Context
        # We replace NaN with None to ensure JSON validity later
        sample_data = df.head(3).where(pd.notnull(df), None).to_dict(orient='records')
        
        return {
            "headers": headers,
            "sample_data": sample_data,
            "row_count": len(df),
            "file_type": "excel/csv"
        }
    except Exception as e:
        activity.logger.error(f"Extraction failed: {str(e)}")
        raise e

@activity.defn
async def generate_mapping_proposal(
    extraction_data: Dict[str, Any], 
    target_doctype: str, 
    source_system: str = "Generic"
) -> Dict[str, Any]:
    """
    Calls Google Gemini Flash (REST API) to generate the mapping proposal.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    # Use the stable alias
    MODEL_NAME = "gemini-flash-latest" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"

    headers = extraction_data["headers"]
    sample_data = extraction_data["sample_data"]
    
    activity.logger.info(f"Connecting to Gemini Flash to analyze {len(headers)} columns...")

    # 1. Fetch Knowledge Base Context
    known_map = kb.get_known_mapping(source_system)
    target_fields = kb.get_erpnext_schema(target_doctype)

    # 2. Construct Prompt
    full_prompt = (
        f"{SYSTEM_PROMPT_ANALYZER.format(target_doctype=target_doctype, target_fields=', '.join(target_fields))}\n"
        f"----------------\n"
        f"{USER_PROMPT_TEMPLATE.format(source_system=source_system, headers=headers, sample_data=json.dumps(sample_data), kb_context=str(known_map))}"
    )

    # 3. Prepare Payload
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }
    
    request_headers = {"Content-Type": "application/json"}

    # 4. Execute REST Call with Retries (Logic from ai_service.py)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=request_headers, json=payload) as resp:
                    
                    if resp.status == 429:
                        wait_time = 15 * (attempt + 1)
                        activity.logger.warn(f"Rate Limit Hit (429). Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue 

                    if resp.status != 200:
                        text = await resp.text()
                        activity.logger.error(f"Gemini Error {resp.status}: {text}")
                        # Return empty mapping on failure to prevent crash
                        return {"mappings": {}, "error": f"HTTP {resp.status}"}
                    
                    result = await resp.json()
                    
                    try:
                        raw_text = result['candidates'][0]['content']['parts'][0]['text']
                        # Clean Markdown if present
                        clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                        parsed_json = json.loads(clean_text)
                        
                        activity.logger.info(f"Gemini Analysis Complete. Confidence: {parsed_json.get('confidence', 0)}")
                        return parsed_json
                        
                    except Exception as parse_err:
                        activity.logger.error(f"Parsing Error: {parse_err}")
                        return {"mappings": {}, "error": "Parsing Failed"}

        except Exception as e:
            activity.logger.error(f"Connection Failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                return {"mappings": {}, "error": str(e)}

    return {"mappings": {}, "error": "Max retries exceeded"}

@activity.defn
async def transform_and_upload(
    s3_key: str, 
    approved_mapping: Dict[str, str], 
    company_slug: str
) -> str:
    """
    Applies the User-Confirmed mapping to the full dataset and saves as CSV.
    """
    activity.logger.info("Starting Transformation Phase...")
    
    # 1. Load Data
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    file_content = response['Body'].read()
    
    if s3_key.endswith('.xlsx'):
        df = pd.read_excel(io.BytesIO(file_content))
    else:
        df = pd.read_csv(io.BytesIO(file_content))

    # --- CRITICAL FIX: STRIP WHITESPACE FROM HEADERS ---
    # This handles "Party Name " vs "Party Name" mismatches
    df.columns = df.columns.str.strip()
    
    activity.logger.info(f"Normalized File Headers: {list(df.columns)}")
    activity.logger.info(f"Requested Mapping: {approved_mapping}")

    # 2. Filter Valid Mappings
    # Only keep mappings where the Source Column actually exists in the file
    valid_map = {}
    for source_col, target_col in approved_mapping.items():
        if not target_col: 
            continue # Skip null mappings
            
        clean_source = source_col.strip() # Ensure key is also stripped
        
        if clean_source in df.columns:
            valid_map[clean_source] = target_col
        else:
            activity.logger.warning(f"⚠️ Mapping skipped: Column '{clean_source}' not found in file.")

    if not valid_map:
        raise ValueError(f"Transformation failed: None of the provided keys {list(approved_mapping.keys())} matched the file columns {list(df.columns)}")

    # 3. Rename Columns
    df = df.rename(columns=valid_map)
    
    # 4. Filter to only keep mapped columns
    # We only select the values that are successfully in the valid_map
    final_cols = list(valid_map.values())
    df_final = df[final_cols]

    # 5. Save to CSV
    output_buffer = io.StringIO()
    df_final.to_csv(output_buffer, index=False)
    
    # 6. Upload
    import uuid
    new_key = f"processed/{company_slug}/import_ready_{uuid.uuid4()}.csv"
    
    s3.put_object(Bucket=S3_BUCKET, Key=new_key, Body=output_buffer.getvalue())
    
    activity.logger.info(f"Transformed file uploaded to: {new_key}")
    return new_key
    
@activity.defn
async def trigger_validation_agent(file_key: str) -> str:
    """
    Stub to notify the Validation Agent.
    """
    activity.logger.info(f"Handoff to Validation Agent for file: {file_key}")
    return "Validation Started"