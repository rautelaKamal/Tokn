import os
from google import genai

api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyC9Voq11q23CdsCvHpJvSsa5iaQOnCPv_M")
client = genai.Client(api_key=api_key)

print("Listing all available models:")
try:
    for m in client.models.list():
        # print all fields/properties
        print(f"- {m.name} | {m.display_name}")
except Exception as e:
    print(f"Failed to list models: {e}")
