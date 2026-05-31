#!/usr/bin/env python
"""Test new API key"""

import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Testing New Google Gemini API Key")
print("="*60)
print()

import os
from dotenv import load_dotenv
load_dotenv()
NEW_API_KEY = os.getenv("GEMINI_KEY_1", "")

try:
    import google.generativeai as genai
    print("✓ Module imported")
    
    genai.configure(api_key=NEW_API_KEY)
    print("✓ API key configured")
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✓ Model initialized (gemini-2.0-flash)")
    
    print()
    print("Testing with simple prompt...")
    response = model.generate_content("Say 'New API key is working perfectly!'")
    
    print()
    print("="*60)
    print("✅ SUCCESS! New API Key Works!")
    print("="*60)
    print()
    print("Response:", response.text)
    print()
    print("🎉 Your app is ready with fresh quota!")
    print("   - 60 requests per minute")
    print("   - 1,500 requests per day")
    
except Exception as e:
    print()
    print("="*60)
    print("❌ ERROR!")
    print("="*60)
    print(f"Error: {e}")
    print()
    if "429" in str(e) or "quota" in str(e).lower():
        print("Quota exceeded on this key too!")
        print("Wait 1 minute and try again.")
    elif "API key not valid" in str(e):
        print("API key is invalid.")
        print("Please check if copied correctly.")
    else:
        print("Other error. Check internet connection.")
