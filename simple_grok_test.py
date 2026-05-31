#!/usr/bin/env python3
"""
Simple Grok API test
"""

from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

# Your API key
GROK_API_KEY = os.getenv("GROK_API_KEY", "")

print("Testing Grok API...")

try:
    client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.x.ai/v1"
    )
    
    # Try different model names
    models_to_try = ["grok-2", "grok-beta", "grok-2-1212", "grok-2-mini"]
    
    for model in models_to_try:
        try:
            print(f"\nTrying model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello! Just say 'Working' if you can respond."}],
                max_tokens=10
            )
            
            print(f"✅ SUCCESS with {model}: {response.choices[0].message.content}")
            break
            
        except Exception as e:
            print(f"❌ Failed with {model}: {str(e)[:100]}...")
            continue
    
except Exception as e:
    print(f"❌ General error: {e}")