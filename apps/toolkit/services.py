from decimal import Decimal

import httpx
from django.conf import settings


class LLMError(Exception):
    """Raised when the model provider fails or returns something unusable."""


def _post(url, payload, timeout, headers=None):
    """POST JSON and return the parsed body. Every transport failure becomes LLMError."""
    try:
        response = httpx.post(url, json=payload, headers=headers or {}, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise LLMError("The model took too long to respond.") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Model provider returned {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        raise LLMError("Could not reach the model provider.") from exc
    return response.json()


def _call_ollama(messages, temperature=0.2):
    """Call a local Ollama server. Returns the normalized result dict."""
    data = _post(
        settings.OLLAMA_URL,
        {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        settings.OLLAMA_TIMEOUT,
    )

    try:
        return {
            "text": data["message"]["content"],
            "input_tokens": data["prompt_eval_count"],
            "output_tokens": data["eval_count"],
            "finish_reason": data["done_reason"],
            "model": settings.OLLAMA_MODEL,
        }
    except KeyError as exc:
        raise LLMError(f"Unexpected Ollama response: missing {exc}.") from exc


def _call_groq(messages, temperature=0.2):
    """Call the Groq API. Returns the normalized result dict."""
    if not settings.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY is not set.")

    data = _post(
        settings.GROQ_URL,
        {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
        },
        settings.GROQ_TIMEOUT,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
    )

    try:
        choice = data["choices"][0]
        return {
            "text": choice["message"]["content"],
            "input_tokens": data["usage"]["prompt_tokens"],
            "output_tokens": data["usage"]["completion_tokens"],
            "finish_reason": choice["finish_reason"],
            "model": settings.GROQ_MODEL,
        }
    except (KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected Groq response: {exc}.") from exc


PROVIDERS = {
    "ollama": _call_ollama,
    "groq": _call_groq,
}


def call_llm(messages, temperature=0.2):
    """Send messages to the configured provider."""
    provider = PROVIDERS.get(settings.LLM_PROVIDER)
    if provider is None:
        raise LLMError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}.")
    return provider(messages, temperature=temperature)


SUMMARIZE_SYSTEM = "You are a concise summarizer. Reply with the summary only, no preamble."

REWRITE_SYSTEM = (
    "You rewrite text in a requested tone. Preserve the meaning and every fact. "
    "Reply with the rewritten text only, no preamble and no commentary."
)

TRANSLATE_SYSTEM = (
    "You are a translator. Translate the user's text into the requested language, "
    "preserving meaning and tone. Reply with the translation only, no preamble "
    "and no commentary."
)

TRUNCATED_REASONS = {"length", "max_tokens"}


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


def _run(messages, output_key, temperature=0.2):
    """Call the provider and shape the response body every endpoint returns."""
    result = call_llm(messages, temperature=temperature)
    return {
        output_key: result["text"].strip(),
        "provider": settings.LLM_PROVIDER,
        "model": result["model"],
        "truncated": result["finish_reason"] in TRUNCATED_REASONS,
        "usage": {
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        },
        "cost_usd": "0.000000",
        "equivalent_cost_usd": equivalent_cost(
            result["input_tokens"], result["output_tokens"]
        ),
    }


def summarize(text):
    """Summarize text. Returns a dict ready for the API response."""
    return _run(
        [
            {"role": "system", "content": SUMMARIZE_SYSTEM},
            {"role": "user", "content": f"Summarize the following text:\n\n{text}"},
        ],
        "summary",
    )


def rewrite(text, tone):
    """Rewrite text in the given tone."""
    return _run(
        [
            {"role": "system", "content": REWRITE_SYSTEM},
            {
                "role": "user",
                "content": f"Rewrite the following text in a {tone} tone:\n\n{text}",
            },
        ],
        "rewrite",
        temperature=0.8,
    )


def translate(text, target_language):
    """Translate text into the target language."""
    return _run(
        [
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {
                "role": "user",
                "content": f"Translate the following text into {target_language}:\n\n{text}",
            },
        ],
        "translation",
    )
