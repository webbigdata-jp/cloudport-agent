---
name: gemini-to-qwen-api-mapping
description: Translate Google Gemini SDK (google-genai) code to Qwen Cloud's OpenAI-compatible API. Use whenever migrating, porting, or rewriting Python code that imports google.genai or calls generate_content, embed_content, or uses response_schema / Pydantic structured output with Gemini — even if the user only says "move this to Qwen" or "make this run on Alibaba Cloud".
---

# Gemini → Qwen Cloud API Mapping

Core knowledge for rewriting `google-genai` call sites into Qwen Cloud's
OpenAI-compatible API. Derived from a real production migration
(SoccerScope: YouTube analytics pipeline, Gemini → Qwen Cloud).

## Golden rules

1. Change ONLY the LLM call sites. Surrounding business logic, retries,
   file I/O and MongoDB code must stay byte-identical wherever possible.
   Small diffs = reviewable diffs.
2. Never guess model names or parameter names. Check the current
   Qwen Cloud docs (https://docs.qwencloud.com) before writing code —
   model lineups change quarterly.
3. After mapping, ALWAYS run the `migration-validation` skill before
   declaring success.

## Client initialization

| Gemini (google-genai) | Qwen Cloud (OpenAI-compatible) |
|---|---|
| `from google import genai` | `from openai import OpenAI` |
| `client = genai.Client(api_key=...)` | `client = OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")` |
| env: `GEMINI_API_KEY` | env: `DASHSCOPE_API_KEY` |

Note: use the `-intl` endpoint for international accounts. The mainland
endpoint differs. Verify which one the target account uses.

## Text generation

| Gemini | Qwen |
|---|---|
| `client.models.generate_content(model=..., contents=...)` | `client.chat.completions.create(model=..., messages=[{"role":"user","content":...}])` |
| `response.text` | `completion.choices[0].message.content` |
| `system_instruction` in config | `{"role":"system", ...}` message |

Pick the model by task profile (verify current names in docs before use):
high-reasoning → max-tier, balanced → plus-tier, cheap bulk → flash-tier.

## Structured output (Pydantic response_schema)

Gemini accepts a Pydantic class directly via
`config={"response_schema": MyModel}` and returns `response.parsed`.

Qwen (OpenAI-compatible) equivalent — two options, prefer (a):

a. JSON Schema mode: pass the schema explicitly and re-validate:

```python
completion = client.chat.completions.create(
    model=MODEL,
    messages=msgs,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "comment_analysis",
            "schema": MyModel.model_json_schema(),
        },
    },
)
parsed = MyModel.model_validate_json(
    completion.choices[0].message.content
)
```

b. Fallback if json_schema is unsupported by the chosen model:
`response_format={"type": "json_object"}` + embed the schema in the
prompt + `model_validate_json` with a retry loop on ValidationError.

Check per-model structured-output support in the Qwen Cloud
"Structured output" docs — support differs across model tiers.

The Pydantic model itself does NOT need to change. Keep it shared
between old and new code so `migration-validation` can compare.

## Embeddings

| Gemini | Qwen |
|---|---|
| `client.models.embed_content(model=..., contents=...)` | `client.embeddings.create(model=..., input=[...])` |
| `result.embeddings[i].values` | `resp.data[i].embedding` |

CRITICAL: embedding dimensions almost certainly differ between the
Gemini and Qwen embedding models. Consequences:

- Any existing vector index (e.g. MongoDB Atlas `numDimensions`) must
  be recreated with the new dimension.
- Old and new vectors are NOT comparable. Plan a full re-embed backfill
  of the corpus; do not mix vector spaces in one collection/index.

This is the single most common silent failure in Gemini→Qwen ports.

## Error handling & rate limits

- Replace `google.genai.errors.*` exception handling with
  `openai.APIError` / `openai.RateLimitError`.
- Preserve the original backoff/retry semantics; only swap the
  exception classes.

## What NOT to touch

- YouTube Data API code (`google-api-python-client`, `build()`,
  `.list().execute()`) is unrelated to Gemini. Leave it alone.
- MongoDB read/write logic (except vector index dimension, see above).

For a worked end-to-end example (before/after of a real script), see
[examples.md](examples.md).
