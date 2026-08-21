"""
Day 2 scratch — one raw HTTP call to a local model, no Django in the way.

Run:  ./venv/Scripts/python.exe scratch.py
"""

import json
from decimal import Decimal

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"


# Local inference is free. These are what the same request WOULD cost on a
# hosted provider, per 1,000,000 tokens (USD). Verify at https://claude.com/pricing
EQUIVALENT_PRICES = {
    "claude-haiku-4-5": {"input": Decimal("1.00"), "output": Decimal("5.00")},
    "claude-opus-5": {"input": Decimal("5.00"), "output": Decimal("25.00")},
}

print(f"target: {MODEL} at {OLLAMA_URL}")


SYSTEM = "You are a concise summarizer. Reply with the summary only, no preamble"

ARTICLE = (
    "Django is a high-level Python web framework that encourages rapid "
    "development and clean, pragmatic design. Built by experienced developers, "
    "it takes care of much of the hassle of web development, so you can focus "
    "on writing your app without needing to reinvent the wheel."
)

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Summarize this in one sentence:\n\n{ARTICLE}"},
    ],
    "stream": False,
}

print("--- request ---")
print(json.dumps(payload, indent=2))

response = httpx.post(OLLAMA_URL, json=payload, timeout=120.0)
response.raise_for_status()

data = response.json()

text = data["message"]["content"]
input_tokens = data["prompt_eval_count"]
output_tokens = data["eval_count"]
done_reason = data["done_reason"]

print("--- summary ---")
print(text)

print("\n--- usage ---")
print(f"done_reason:   {done_reason}")
print(f"input tokens:  {input_tokens}")
print(f"output tokens: {output_tokens}")
print(f"total time:    {data['total_duration'] / 1_000_000_000:.2f}s")


def equivalent_cost(model_name, input_tokens, output_tokens):
    """What this request would have cost on hoster provider, in USD."""
    rates = EQUIVALENT_PRICES[model_name]
    return (
        Decimal(input_tokens) / Decimal(1_000_000) * rates["input"]
        + Decimal(output_tokens) / Decimal(1_000_000) * rates["output"]
    )


print("\n--- cost ---")
print("actual (local):$0.000000")
for name in EQUIVALENT_PRICES:
    print(f"if {name}: ${equivalent_cost(name, input_tokens, output_tokens):.6f}")
