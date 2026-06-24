"""
Standalone Groq connectivity test.

Run this ONCE after setting GROQ_API_KEY in your .env, before running the
full app, to confirm your key and network setup work:

    python test_groq_connection.py

This makes exactly one short API call and prints the result. If it works,
everything in the main app that talks to Groq (Code Explainer, Ask Questions,
Documentation Generator, Bug Investigation Assistant) will work too — they
all go through the same client code in app/services/llm_client.py.
"""
from app.services.llm_client import call_llm, LLMError

print("Testing connection to Groq...\n")

try:
    response = call_llm(
        messages=[
            {"role": "user", "content": "Reply with exactly: DevLens AI connection test successful."}
        ],
        max_tokens=50,
    )
    print("SUCCESS. Groq responded:")
    print(response)
except LLMError as e:
    print("FAILED. Here's the error DevLens AI would show you in the app:")
    print(str(e))
    print("\nCommon fixes:")
    print("  - Make sure GROQ_API_KEY is set in backend/.env (no quotes, no spaces)")
    print("  - Get a free key at https://console.groq.com/keys if you don't have one")
    print("  - Check your internet connection / firewall isn't blocking api.groq.com")
