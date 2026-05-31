from google import genai
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

# Find working Gemini models
print("=== Gemini Models ===")
try:
    gc = genai.Client(api_key=os.getenv("GEMINI_KEY_1", ""))
    models = gc.models.list()
    for m in models:
        if 'generate' in str(m.supported_actions):
            print(m.name)
except Exception as e:
    print("Error:", e)

# Find working Grok models
print("\n=== Grok Models ===")
try:
    client = OpenAI(api_key=os.getenv("GROK_API_KEY", ""), base_url='https://api.x.ai/v1')
    models = client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print("Error:", e)
