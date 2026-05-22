import os
from google import genai

api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyC9Voq11q23CdsCvHpJvSsa5iaQOnCPv_M")
client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
]

for model in models_to_test:
    print(f"\n--- Testing model: {model} ---")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say hello"
        )
        print(f"Success! Response: {response.text.strip()}")
    except Exception as e:
        print(f"Failed with error: {e}")
