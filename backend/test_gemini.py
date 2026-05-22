import os
import sys
from google import genai

api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyC9Voq11q23CdsCvHpJvSsa5iaQOnCPv_M")
print(f"Testing with API Key: {api_key[:8]}...")

client = genai.Client(api_key=api_key)

models_to_test = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]

for model in models_to_test:
    print(f"\n--- Testing model: {model} ---")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say hello"
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed with error: {e}")
