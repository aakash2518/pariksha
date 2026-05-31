import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GEMINI_KEY_1", "")
genai.configure(api_key=API_KEY)

print("Available models:")
print("-" * 50)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")
        print(f"  Display: {model.display_name}")
        print()
