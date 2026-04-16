import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
]

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


async def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    """Call OpenRouter API with model fallback chain and retry logic."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "AutoFix AI",
    }

    for attempt in range(MAX_RETRIES):
        for model in MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            }

            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

                    if response.status_code == 429:
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Handle empty or missing content
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    content = choices[0].get("message", {}).get("content", "")
                    if not content.strip():
                        continue

                    return content.strip()

            except (httpx.HTTPStatusError, httpx.RequestError, KeyError):
                continue

        # All models failed this round — wait before retrying
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY)

    return json.dumps({"error": "All models failed. Check your OPENROUTER_API_KEY."})


def extract_json(text: str) -> dict:
    """Extract JSON object from LLM response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    for marker in ["```json", "```"]:
        if marker in text:
            start = text.index(marker) + len(marker)
            end = text.index("```", start)
            try:
                return json.loads(text[start:end].strip())
            except (json.JSONDecodeError, ValueError):
                pass

    # Try finding first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    return {"error": "Failed to parse LLM response", "raw": text[:500]}
