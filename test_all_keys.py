from google import genai
import time

import os
from dotenv import load_dotenv
load_dotenv()

API_KEYS = [k for k in [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
] if k]

print("Testing all API keys...")
print("=" * 60)

for i, key in enumerate(API_KEYS, 1):
    print(f"\nTesting Key {i}: {key[:20]}...")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Say "Hello" in one word'
        )
        print(f"✅ Key {i} WORKING - Response: {response.text.strip()}")
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"❌ Key {i} QUOTA EXCEEDED")
        elif "API key not valid" in error_msg or "INVALID" in error_msg:
            print(f"❌ Key {i} INVALID")
        else:
            print(f"❌ Key {i} ERROR: {error_msg[:100]}")
    
    time.sleep(1)  # Wait between tests

print("\n" + "=" * 60)
print("Test complete!")
