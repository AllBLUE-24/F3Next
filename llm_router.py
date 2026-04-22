import os
import asyncio
import time
from itertools import cycle
from dotenv import load_dotenv

load_dotenv()

# Load the comma-separated string and split it into a list
keys_string = os.getenv("GEMINI_API_KEYS", "")
if not keys_string:
    keys_string = os.getenv("GEMINI_API_KEY", "")

api_keys = [key.strip() for key in keys_string.split(",") if key.strip()]

if not api_keys:
    print("[Warning] No GEMINI_API_KEYS or GEMINI_API_KEY found in environment.")

# Create the infinite loop
key_pool = cycle(api_keys) if api_keys else None

# Model fallback chain: try primary model first, then fall back to cheaper models
FALLBACK_MODELS = ["gemini-1.5-flash"]


async def invoke_smart_llm(messages, model_name="gemini-flash-latest", temperature=0.1, max_output_tokens=800, **kwargs):
    """
    A drop-in replacement/wrapper for ChatGoogleGenerativeAI calls.
    Automatically rotates keys if it hits a quota limit.
    Falls back to gemini-1.5-flash if all keys exhausted on primary model.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    
    for current_model in models_to_try:
        max_attempts = len(api_keys) + 1 if api_keys else 1
        
        for attempt in range(max_attempts):
            current_key = next(key_pool) if key_pool else None
            
            try:
                llm = ChatGoogleGenerativeAI(
                    model=current_model,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    google_api_key=current_key,
                    **kwargs
                )
                
                response = await llm.ainvoke(messages)
                if isinstance(response.content, list):
                    content_str = " ".join(p.get("text", "") for p in response.content if isinstance(p, dict) and "text" in p)
                    try:
                        response.content = content_str
                    except Exception:
                        class DummyResponse:
                            def __init__(self, c):
                                self.content = c
                        return DummyResponse(content_str)
                return response
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str:
                    print(f"[Warning] Quota hit on {current_model}. Rotating key (Attempt {attempt+1}/{max_attempts})...")
                    # Always sleep between rotations to avoid burning keys instantly
                    await asyncio.sleep(min(2 ** attempt, 8))
                    continue
                
                raise e
        
        # All keys exhausted for this model — try fallback
        if current_model != models_to_try[-1]:
            print(f"[Warning] All keys exhausted for {current_model}. Falling back to next model...")
            await asyncio.sleep(2)
            
    raise Exception("Critical: All Gemini API keys and fallback models are out of quota!")

def invoke_smart_llm_sync(messages, model_name="gemini-flash-latest", temperature=0.1, max_output_tokens=800, **kwargs):
    """
    Sync equivalent with model fallback chain.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    
    for current_model in models_to_try:
        max_attempts = len(api_keys) + 1 if api_keys else 1
        
        for attempt in range(max_attempts):
            current_key = next(key_pool) if key_pool else None
            
            try:
                llm = ChatGoogleGenerativeAI(
                    model=current_model,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    google_api_key=current_key,
                    **kwargs
                )
                
                response = llm.invoke(messages)
                if isinstance(response.content, list):
                    content_str = " ".join(p.get("text", "") for p in response.content if isinstance(p, dict) and "text" in p)
                    try:
                        response.content = content_str
                    except Exception:
                        class DummyResponse:
                            def __init__(self, c):
                                self.content = c
                        return DummyResponse(content_str)
                return response
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str:
                    print(f"[Warning] Quota hit on {current_model}. Rotating key (Attempt {attempt+1}/{max_attempts})...")
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise e
        
        # All keys exhausted for this model — try fallback
        if current_model != models_to_try[-1]:
            print(f"[Warning] All keys exhausted for {current_model}. Falling back to next model...")
            time.sleep(2)
            
    raise Exception("Critical: All Gemini API keys and fallback models are out of quota!")
