#!/usr/bin/env python
"""Test if API key works"""

import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Testing Google Gemini API Key")
print("="*60)
print()

import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("GEMINI_KEY_1", "")

try:
    import google.generativeai as genai
    print("✓ Module imported")
    
    genai.configure(api_key=API_KEY)
    print("✓ API key configured")
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✓ Model initialized")
    
    print()
    print("Testing with simple prompt...")
    response = model.generate_content("Say 'API key is working!'")
    
    print()
    print("="*60)
    print("✅ SUCCESS! API Key is Valid!")
    print("="*60)
    print()
    print("Response:", response.text)
    print()
    print("Your app is ready to use!")
    
except Exception as e:
    print()
    print("="*60)
    print("❌ ERROR!")
    print("="*60)
    print(f"Error: {e}")
    print()
    if "API key not valid" in str(e):
        print("API key is invalid. Please check:")
        print("1. Key copied correctly?")
        print("2. No extra spaces?")
        print("3. Complete key copied?")
    else:
        print("Other error occurred. Check internet connection.")
