import os
import asyncio
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

async def invoke_smart_llm(messages, model_name="gemini-flash-latest", temperature=0.1, max_output_tokens=800, **kwargs):
    """
    A drop-in replacement/wrapper for ChatGoogleGenerativeAI calls.
    Automatically rotates keys if it hits a quota limit.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    max_attempts = len(api_keys) + 1 if api_keys else 1
    
    for attempt in range(max_attempts):
        current_key = next(key_pool) if key_pool else None
        
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                google_api_key=current_key,
                **kwargs
            )
            
            response = await llm.ainvoke(messages)
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            # Catch 429 quota/resource exhausted exceptions LangChain wraps
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str:
                print(f"[Warning] Quota or Rate limit hit. Rotating to next Gemini key (Attempt {attempt+1}/{max_attempts})...")
                # Wait a bit if we only have 1 key to allow rate limit to clear
                if len(api_keys) <= 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            
            # If it's a real error (bad prompt, etc), raise it
            raise e
            
    raise Exception("Critical: All Gemini API keys are out of quota or failed repeatedly!")

def invoke_smart_llm_sync(messages, model_name="gemini-flash-latest", temperature=0.1, max_output_tokens=800, **kwargs):
    """
    Sync equivalent.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    max_attempts = len(api_keys) + 1 if api_keys else 1
    
    for attempt in range(max_attempts):
        current_key = next(key_pool) if key_pool else None
        
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                google_api_key=current_key,
                **kwargs
            )
            
            response = llm.invoke(messages)
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str:
                print(f"[Warning] Quota hit. Rotating to next Gemini key (Attempt {attempt+1}/{max_attempts})...")
                import time
                if len(api_keys) <= 1:
                    time.sleep(2 ** attempt)
                continue
            raise e
            
    raise Exception("Critical: All Gemini API keys are out of quota or failed repeatedly!")
