# AI Text Toolkit

A Django + DRF service exposing LLM-backed text endpoints — summarize, rewrite, translate —
where every response carries its own token accounting and cost estimate.

> **Status: in progress.** Week 1 of a structured build. The raw model integration works
> end to end as a standalone script; the Django layer is being built on top of it next.

---

## What it does

Three endpoints, each doing one text task through a language model:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/summarize/` | condense text to a short summary |
| `POST /api/v1/rewrite/` | rewrite text in a requested tone |
| `POST /api/v1/translate/` | translate text to a target language |

Every response returns the result **plus the input/output token counts and an estimated
cost**, and degrades gracefully when the model is slow or unavailable.

---

## Why token counts and cost are first-class

Most demo projects call a model and return the text. In production, an LLM call is a
metered, latency-variable, occasionally-failing network dependency — so this service
treats usage accounting as part of the response contract rather than an afterthought.

Reporting input and output tokens **separately** is deliberate: hosted providers charge
roughly 5× more for output than input, because input is processed in a single parallel
pass while output requires one forward pass per generated token. A single "total tokens"
number hides where the money actually goes.

---

## Architecture

```
POST /api/v1/summarize/
      │
      ├─ config/urls.py          route
      ├─ apps/toolkit/serializers.py   validate input (incl. token-length limits)
      ├─ apps/toolkit/views.py         thin: validate → call service → return
      ├─ apps/toolkit/services.py      all LLM logic lives here
      │        │
      │        └─ HTTP → model provider
      │
      └─ core/renderers.py       wrap as {data, error, message}
```

**Views stay thin.** Business logic and every model call live in `services.py`. Input is
validated with DRF serializers before any request is sent — which is also where oversized
input is rejected, since a large document is both a context-window failure and a cost risk.

All responses use a consistent envelope:

```json
{ "data": {...}, "error": null, "message": "OK" }
```

---

## Stack

- **Django + Django REST Framework**
- **httpx** — the model API is called over plain HTTP rather than through a vendor SDK,
  so the provider stays swappable
- **Ollama** (`llama3.1:8b`) for local development
- PostgreSQL, Redis, and Celery are planned for later phases; Week 1 is deliberately a
  single synchronous request path with no datastore.

### Why a local model in development

Development runs against a model served locally by [Ollama](https://ollama.com), which
keeps iteration free and unmetered while the plumbing is built. The service layer is
written provider-agnostically, so a hosted provider can be swapped in for deployment by
changing configuration rather than code.

The providers differ in details that a naive integration would hard-code — where the
system prompt goes, where sampling parameters live, whether the response text is a string
or a list of typed blocks. Absorbing those differences in one place is the point of the
service layer.

Because local inference costs nothing, cost reporting is computed as an **equivalent
cost** — what the same token counts would have cost on a hosted model — so the accounting
logic is real and testable rather than stubbed.

---

## Running it locally

**Requirements:** Python 3.13, [Ollama](https://ollama.com/download)

```bash
# 1. Pull a model (~4.9 GB)
ollama pull llama3.1:8b

# 2. Create the environment
python -m venv venv
./venv/Scripts/python.exe -m pip install httpx      # Windows
# source venv/bin/activate && pip install httpx     # macOS / Linux

# 3. Run the standalone integration script
./venv/Scripts/python.exe scratch.py
```

`scratch.py` is the model integration with no framework around it: it builds the request,
sends it, parses the response, and reports token usage and equivalent cost. It exists to
keep the model-facing logic understandable in isolation before it moves into
`apps/toolkit/services.py`.

Sample output:

```
--- summary ---
Django is a Python web framework that simplifies development by handling tasks,
allowing developers to focus on app creation.

--- usage ---
done_reason:   stop
input tokens:  90
output tokens: 26
total time:    1.55s

--- cost ---
actual (local):      $0.000000
if claude-haiku-4-5: $0.000220
if claude-opus-5:    $0.001100
```

---

## Roadmap

- [x] Model integration over raw HTTP — request, response parsing, token usage
- [x] Cost calculation (`Decimal`-based, per-model rate table)
- [ ] Django project skeleton — split settings, `.env`, `{data, error, message}` renderer
- [ ] `POST /api/v1/summarize/` end to end
- [ ] Timeout, retry, and provider-failure handling
- [ ] `POST /api/v1/rewrite/` and `POST /api/v1/translate/`
- [ ] Deployment against a hosted provider

---

## Notes

- Secrets are loaded from a gitignored `.env`; `.env.example` documents the required
  variables. No credentials are committed.
- Rate tables in code are a snapshot and should be verified against current provider
  pricing before being relied on.
- Model output is non-deterministic by default. Tests assert response **structure**
  (a non-empty result, a clean stop reason, correct cost arithmetic) — never exact
  generated text.
