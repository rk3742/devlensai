"""
LLM client abstraction. Supports Groq (recommended, cloud, free-tier) and
Ollama (fully offline, local). Both expose the same call_llm() interface so
the rest of the app never needs to know which provider is active.
"""
import json
import time
from typing import Optional

import httpx

from app.config import settings


class LLMError(Exception):
    """Raised when the LLM call fails in a way the user should be told about clearly."""
    pass


def _call_groq(messages: list[dict], temperature: float, max_tokens: int, json_mode: bool) -> str:
    if not settings.groq_api_key:
        raise LLMError(
            "No Groq API key configured. Set GROQ_API_KEY in your .env file. "
            "Get a free key at https://console.groq.com/keys"
        )

    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error = None
    for attempt in range(3):
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", 2 ** attempt))
                if attempt < 2:
                    time.sleep(min(retry_after, 10))
                    continue
                raise LLMError(
                    "Groq's free-tier rate limit was hit (too many requests right now). "
                    "Wait a moment and try again."
                )
            if resp.status_code == 401:
                raise LLMError("Groq rejected the API key. Double-check GROQ_API_KEY in your .env file.")
            if resp.status_code >= 400:
                raise LLMError(f"Groq API returned an error ({resp.status_code}): {resp.text[:300]}")

            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.ConnectError as e:
            last_error = e
            raise LLMError(
                "Couldn't reach Groq's API. Check your internet connection. "
                f"Details: {str(e)[:150]}"
            )
        except httpx.TimeoutException:
            last_error = "timeout"
            if attempt < 2:
                continue
            raise LLMError("Groq API timed out after multiple attempts. Try again shortly.")

    raise LLMError(f"Groq API call failed after retries: {last_error}")


def _call_ollama(messages: list[dict], temperature: float, max_tokens: int, json_mode: bool) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if json_mode:
        payload["format"] = "json"

    try:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=180,
        )
        if resp.status_code != 200:
            raise LLMError(
                f"Ollama returned an error ({resp.status_code}). Is Ollama running and is the "
                f"model '{settings.ollama_model}' pulled? Try: ollama pull {settings.ollama_model}"
            )
        data = resp.json()
        return data["message"]["content"]
    except httpx.ConnectError:
        raise LLMError(
            f"Couldn't connect to Ollama at {settings.ollama_base_url}. "
            "Make sure Ollama is installed and running (run `ollama serve`)."
        )
    except httpx.TimeoutException:
        raise LLMError(
            "Ollama took too long to respond. Local models can be slow on limited hardware "
            "— consider switching AI_PROVIDER to 'groq' in your .env for faster responses."
        )


def call_llm(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 1200,
    json_mode: bool = False,
) -> str:
    """
    Sends a chat-style request to whichever provider is configured.
    Raises LLMError with a user-friendly message on any failure.
    """
    if settings.ai_provider == "ollama":
        return _call_ollama(messages, temperature, max_tokens, json_mode)
    return _call_groq(messages, temperature, max_tokens, json_mode)


def call_llm_json(messages: list[dict], temperature: float = 0.1, max_tokens: int = 1200) -> dict:
    """Calls the LLM expecting a JSON object back, with a defensive parse fallback."""
    raw = call_llm(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some models wrap JSON in markdown fences despite instructions; strip and retry.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            raise LLMError(f"AI response wasn't valid JSON. Raw response started with: {raw[:200]}")
