"""
Quick API verification script for Groq Fallback in AI Documentary Maker.
Reads GROQ_API_KEY safely from environment variables (never hardcoded).
Usage:
    export GROQ_API_KEY="your_key"
    python test_groq_fallback.py
"""
import json
import os
import sys
import urllib.error
import urllib.request


def main():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # 1. Check live accessible models for this API key
    models_url = "https://api.groq.com/openai/v1/models"
    req_models = urllib.request.Request(
        models_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AIDocumentaryMakerTest/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req_models, timeout=20) as resp:
        models_data = json.loads(resp.read().decode("utf-8"))
    available = sorted(
        m["id"] for m in models_data.get("data", []) if isinstance(m, dict) and "id" in m
    )
    print("Available models on this account:", available)

    target_model = next(
        (m for m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"] if m in available),
        None,
    )
    if not target_model:
        print("ERROR: No preferred production text generation model found!", file=sys.stderr)
        sys.exit(1)

    # 2. Run a real JSON mode chat completion test
    chat_url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": "Return ONLY valid JSON."},
            {
                "role": "user",
                "content": 'Return JSON with keys "status" ("ok") and "scene_query" (a 3-word English nature video search query).',
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req_chat = urllib.request.Request(
        chat_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AIDocumentaryMakerTest/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_chat, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        print(f"SUCCESS using {target_model}:", parsed)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP {e.code} Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
