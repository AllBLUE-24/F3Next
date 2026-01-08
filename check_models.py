import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def list_available_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print(f"🔑 Checking models for key starting with: {api_key[:5]}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"❌ API Error {resp.status}: {await resp.text()}")
                print("\n💡 DIAGNOSIS: If this failed, you might be using a Vertex AI Key.")
                print("   Vertex AI keys do NOT work with 'generativelanguage.googleapis.com'.")
                print("   Please get a key from: https://aistudio.google.com/app/apikey")
                return

            data = await resp.json()
            print("\n✅ AVAILABLE MODELS:")
            found_flash = False
            for m in data.get('models', []):
                name = m['name'].replace('models/', '')
                print(f" - {name}")
                if 'flash' in name:
                    found_flash = True

            print("-" * 30)
            if found_flash:
                print("✅ 'flash' is available! We just need to use the exact name printed above.")
            else:
                print("⚠️ 'flash' is NOT in your list. Use 'gemini-pro' instead.")

if __name__ == "__main__":
    asyncio.run(list_available_models())