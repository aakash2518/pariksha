from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
print(client.models.list())
