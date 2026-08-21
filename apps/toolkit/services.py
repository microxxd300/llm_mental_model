from decimal import Decimal

import httpx
from django.conf import settings


class LLMError(Exception):
    """Raised when the model provider fails or returns something unusable."""


def _call_ollama(messages, temperature=0.2):
    """POST messages to Ollama. Returns (text, input_tokens, output_tokens, done_reason)."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        response = httpx.post(
            settings.OLLAMA_URL,
            json=payload,
            timeout=settings.OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMError("The model took too long to respond.") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Model provider returned {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        raise LLMError("Could not reach the model provider.") from exc

    data = response.json()

    try:
        return (
            data["message"]["content"],
            data["prompt_eval_count"],
            data["eval_count"],
            data["done_reason"],
        )
    except KeyError as exc:
        raise LLMError(f"Unexpected response from provider: missing {exc}.") from exc


SUMMARIZE_SYSTEM = "You are a concise summarizer. Reply with the summary only, no preamble."


def equivalent_cost(input_tokens, output_tokens):
    """What this request would have cost on each hosted provider, in USD."""
    costs = {}
    for name, rates in settings.EQUIVALENT_PRICES.items():
        total = (
            Decimal(input_tokens) / Decimal(1_000_000) * rates["input"]
            + Decimal(output_tokens) / Decimal(1_000_000) * rates["output"]
        )
        costs[name] = f"{total:.6f}"
    return costs


def summarize(text):
    """Summarize text. Returns a dict ready for the API response."""
    messages = [
        {"role": "system", "content": SUMMARIZE_SYSTEM},
        {"role": "user", "content": f"Summarize the following text:\n\n{text}"},
    ]

    content, input_tokens, output_tokens, done_reason = _call_ollama(messages)

    return {
        "summary": content.strip(),
        "model": settings.OLLAMA_MODEL,
        "truncated": done_reason == "length",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }, 
        "cost_usd": "0.000000",
        "equivalent_cost_usd": equivalent_cost(input_tokens, output_tokens),
    }
