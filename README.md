# AI Text Toolkit

A Django + DRF service exposing LLM-backed text endpoints — summarize, rewrite, translate —
where every response carries its own token accounting and cost estimate.

**Live API:** https://llm-mental-model.vercel.app
**Live app:** https://llm-mental-model-frontend.vercel.app ·
[frontend repo](https://github.com/microxxd300/llm_mental_model_frontend)

```bash
curl -X POST https://llm-mental-model.vercel.app/api/v1/summarize/ \
  -H "Content-Type: application/json" \
  -d '{"text":"Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design."}'
```

---

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/api/v1/health/` | — | `{"status": "ok"}` |
| `POST` | `/api/v1/summarize/` | `text` | `summary` |
| `POST` | `/api/v1/rewrite/` | `text`, `tone` | `rewrite` |
| `POST` | `/api/v1/translate/` | `text`, `target_language` | `translation` |

`text` is 20–10,000 characters. `tone` is one of `neutral`, `formal`, `casual`,
`confident`, `friendly` (default `neutral`). `target_language` is free text, up to 40
characters.

Every response uses the same envelope:

```json
{
  "data": {
    "summary": "Django is a Python web framework for rapid, clean development.",
    "provider": "groq",
    "model": "openai/gpt-oss-20b",
    "truncated": false,
    "usage": { "input_tokens": 129, "output_tokens": 104 },
    "cost_usd": "0.000000",
    "equivalent_cost_usd": {
      "claude-haiku-4-5": "0.000649",
      "claude-opus-5": "0.003245"
    }
  },
  "error": null,
  "message": "OK"
}
```

| Status | When |
|---|---|
| `200` | success |
| `400` | input failed validation — **no model call was made** |
| `429` | per-IP rate limit reached |
| `503` | the model provider timed out, errored, or was unreachable |

Errors use the same envelope with `data: null` and the detail under `error`.

---

## Why token counts and cost are first-class

Most demo projects call a model and return the text. In production an LLM call is a
metered, latency-variable, occasionally-failing network dependency — so this service
treats usage accounting as part of the response contract rather than an afterthought.

Input and output tokens are reported **separately** because hosted providers charge
roughly 5× more for output: input is processed in a single parallel pass, while output
requires one forward pass per generated token. A combined "total tokens" figure hides
where the money actually goes.

Local inference is free, so `cost_usd` is honestly `0.000000` and
`equivalent_cost_usd` reports what the same token counts would have cost on a hosted
model. That keeps the cost arithmetic real and testable rather than stubbed.

---

## Architecture

```
POST /api/v1/summarize/
      │
      ├─ config/urls.py               route to the app
      ├─ apps/toolkit/serializers.py  validate input, reject oversized text
      ├─ apps/toolkit/views.py        thin: validate → call service → return
      ├─ apps/toolkit/services.py     all LLM logic lives here
      │        └─ HTTP → Ollama or Groq
      └─ core/renderers.py            wrap as {data, error, message}
```

**Views are thin.** Business logic and every model call live in `services.py`. `LLMView`
owns the parts that must never differ between endpoints — validation, error handling,
status codes — and each concrete view supplies only its serializer and service call.

**The provider is swappable.** `services.py` normalizes Ollama and Groq into one result
shape, so `LLM_PROVIDER` selects between a local model in development and a hosted one in
production without touching anything above it. Every transport failure is wrapped in
`LLMError`, so the view catches a single exception type and knows nothing about HTTP
clients.

**Input is validated before anything is spent.** A 10,000-character ceiling caps context
usage, cost, and request duration in one guard, and rejects at the serializer — before a
single token is billed.

**Rate limited per IP**, with one shared `llm` scope across all three endpoints so
rotating endpoints cannot multiply the budget. Counters live in the local-memory cache, so
limits are per-process and best-effort on serverless; a hard limit would need a shared
cache such as Redis.

---

## Stack

- **Django 6.1 + Django REST Framework**
- **httpx** — the model API is called over plain HTTP rather than a vendor SDK, so the
  provider stays swappable
- **Ollama** (`llama3.1:8b`) locally, **Groq** (`openai/gpt-oss-20b`) in production
- **ruff** for linting and formatting
- Deployed on Vercel. No database, no Celery, no Redis — this is a stateless API, which is
  also what lets it run on a free tier.

---

## Running it locally

**Requirements:** Python 3.13, [Ollama](https://ollama.com/download)

```bash
ollama pull llama3.1:8b

python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements-dev.txt   # Windows
# source venv/bin/activate && pip install -r requirements-dev.txt  # macOS / Linux

cp .env.example .env      # then fill in DJANGO_SECRET_KEY
./venv/Scripts/python.exe manage.py runserver
```

### Environment

| Variable | Required | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_SETTINGS_MODULE` | production | `config.settings.prod` |
| `DJANGO_ALLOWED_HOSTS` | production | comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | production | comma-separated origins, no trailing slash |
| `LLM_PROVIDER` | no | `ollama` (default) or `groq` |
| `GROQ_API_KEY` | if using Groq | |
| `GROQ_MODEL`, `GROQ_URL` | no | have defaults |
| `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT` | no | have defaults |

Settings are split into `config/settings/{base,dev,prod}.py`. `base.py` holds what is true
everywhere; `dev.py` and `prod.py` import it and override only what differs, so production
configuration is short enough to audit at a glance.

### Checks

```bash
./venv/Scripts/python.exe -m ruff format .
./venv/Scripts/python.exe -m ruff check .
./venv/Scripts/python.exe manage.py check --deploy --settings=config.settings.prod
```

---

## Notes

- Secrets load from a gitignored `.env`; `.env.example` documents the required variables.
  Nothing sensitive is committed.
- Missing required settings raise at import, so a misconfigured deploy fails to start
  rather than serving traffic with a fallback secret key.
- Rate tables in settings are a snapshot and should be checked against current provider
  pricing before being relied on.
- Model output is non-deterministic. Tests should assert response **structure** — a
  non-empty result, a clean stop reason, correct cost arithmetic — never exact generated
  text.

## Roadmap

- [x] Model integration over raw HTTP — request, response parsing, token usage
- [x] Cost calculation (`Decimal`-based, per-model rate table)
- [x] Django skeleton — split settings, `.env`, `{data, error, message}` renderer
- [x] `POST /api/v1/summarize/` end to end
- [x] Swappable provider layer (Ollama / Groq) behind one interface
- [x] Per-IP rate limiting
- [x] Deployed, with a React client
- [x] `POST /api/v1/rewrite/` and `POST /api/v1/translate/`
- [ ] Retries with backoff on transient provider errors
- [ ] Test suite
