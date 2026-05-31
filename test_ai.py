import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
import google.generativeai as genai

import os
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_KEY_1", "")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(model_name='gemini-2.0-flash')
    
    response = model.generate_content("Say 'AI is working!'")
    print("✅ AI Module Working!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
