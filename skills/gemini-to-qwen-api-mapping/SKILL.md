---
name: gemini-to-qwen-api-mapping
description: Translate Google Gemini SDK (google-genai) code to Alibaba Cloud Model Studio's Qwen OpenAI-compatible API. Use for text, image, video, thinking, embeddings, structured output, or Gemini-style compatibility layers whenever code imports google.genai, calls generate_content/embed_content, uses Part.from_uri, ThinkingConfig, response_schema, or must move from Gemini to Qwen.
---

# Gemini → Qwen API Mapping

Rewrite Gemini model call sites into Qwen / Model Studio patterns while keeping
business logic and UI structure as unchanged as practical.

This skill contains provider-level rules. Project paths, deployment method, and
accepted models belong in the project profile. Before declaring the migration
complete, always invoke `migration-validation`.

## Golden rules

1. **Inventory before editing.** Classify every model call as text, image,
   video, embedding, structured output, tool use, or reasoning-heavy.
2. **Use current official documentation.** Model names, modality support,
   thinking defaults, parameter limits, and endpoints change. Never infer
   support from a family name alone.
3. **Map by task profile, not static model-name equivalence.** A source
   "Pro/Flash/Lite" picker may become several target models chosen by quality,
   latency, cost, region availability, and required modalities.
4. **Preserve the smallest stable surface.** Leave unrelated business logic,
   Google APIs, retries, file I/O, database code, and UI layout unchanged unless
   validation exposes an existing defect.
5. **Do not hide source defects in a converter.** A compatibility layer may
   defensively reject or flatten malformed input, but also fix the bad call
   site and add a regression test.

## Client and endpoint

| Gemini | Qwen / Model Studio |
|---|---|
| `from google import genai` | `from openai import OpenAI` |
| `genai.Client(...)` | `OpenAI(api_key=..., base_url=..., timeout=...)` |
| `GEMINI_API_KEY` | `DASHSCOPE_API_KEY` |
| `response.text` | `completion.choices[0].message.content` |

Prefer an explicit workspace-scoped `DASHSCOPE_BASE_URL`. The API key and
endpoint must belong to the same region/workspace. Keep the endpoint
configurable; do not bake one account's region into reusable code.

## Text generation

| Gemini | Qwen OpenAI-compatible |
|---|---|
| `client.models.generate_content(model=..., contents=...)` | `client.chat.completions.create(model=..., messages=[...])` |
| `system_instruction` | system message |
| `max_output_tokens` | `max_completion_tokens` for thinking models when a total cap is needed |

Normalize response content because SDKs/models may return a plain string or a
list of typed text parts. Treat an empty response as an explicit error state,
not as valid Markdown/UI content.

## Multimodal input

OpenAI-compatible message content is an ordered flat list. Preserve the
source order of text and media parts.

- Image URI: `{"type": "image_url", "image_url": {"url": uri}}`
- Video URI: `{"type": "video_url", "video_url": {"url": uri}, "fps": n}`
- Text: `{"type": "text", "text": text}`

For OpenAI-compatible calls, local `file://` paths are not portable. Use a
reachable HTTPS URL or an accepted data URL/Base64 form after checking current
limits. Confirm that Model Studio can fetch remote assets from the selected
region; browser reachability alone is not sufficient.

When one UI selector drives text, image, and video calls, expose only the
intersection of models supporting every required modality. Prefer per-call-site
model selection in production applications.

Read [multimodal-thinking.md](multimodal-thinking.md) before implementing
`Part.from_uri`, video input, or reasoning controls.

## Thinking controls

`enable_thinking` and `thinking_budget` are Qwen-specific, non-standard OpenAI
parameters. With the OpenAI Python SDK, pass them through `extra_body`.

- Auto/model default: omit both fields unless the product explicitly defines a
  default.
- Manual positive budget: `enable_thinking=true` plus `thinking_budget=N`.
- Off: `enable_thinking=false`; do not encode Off as `thinking_budget=0` alone.

For thinking models, `max_completion_tokens` covers reasoning plus the final
answer. When the source UI has a separate answer budget and a manual thinking
budget, preserve that meaning:

```text
max_completion_tokens = answer_budget + thinking_budget + accounting_margin
```

Use a margin at least as large as the documented token-accounting tolerance;
the validated Streamlit example uses 16. Never send a total cap less than or
equal to the thinking budget. If no total cap is required, omit it rather than
inventing one.

## Narrow compatibility layer

Use a compatibility module when many call sites share a small Gemini surface
such as `Part.from_uri`, `GenerateContentConfig`, `ThinkingConfig`, and
`client.models.generate_content`. This keeps application diffs reviewable.

Do not create a broad fake Gemini SDK. Mirror only the symbols actually used,
validate unsupported MIME types/parameters, expose the generated request in
unit tests, and keep provider-native names inside the adapter.

Golden implementation:
`examples/gemini-streamlit-cloudrun-to-qwen-fc/cloudport_compat.py`.

## Structured output

Gemini may accept a Pydantic class as `response_schema`. For Qwen:

1. Prefer a currently supported JSON Schema response format when the chosen
   model documents it.
2. Otherwise use JSON object mode, put the complete schema constraints in the
   prompt, and validate locally with the unchanged Pydantic model.
3. Retry only malformed/invalid output with bounded attempts.
4. Do not assume thinking and structured output combine reliably. Disable
   thinking unless official support and project tests establish otherwise.

## Embeddings

| Gemini | Qwen OpenAI-compatible |
|---|---|
| `client.models.embed_content(...)` | `client.embeddings.create(...)` |
| `result.embeddings[i].values` | `resp.data[i].embedding` |

Embedding vectors from different models are not interchangeable. Verify the
actual output dimension, re-embed the entire corpus, and use a separate vector
collection/index or an atomic migration. Never query a Gemini vector space
with Qwen query vectors as though they were equivalent.

## Error handling

- Replace Gemini exception classes with the OpenAI SDK equivalents while
  preserving retry/backoff behavior.
- Separate transport/rate-limit failures from invalid parameters, remote-media
  fetch failures, safety filters, and schema validation errors.
- In interactive apps, catch API errors at the UI boundary and show a concise
  provider-branded message; retain details in logs or a collapsible diagnostic
  section.

## What not to touch

Do not remove or rewrite unrelated Google integrations merely because their
package/import names begin with `google`:

- YouTube Data API and Google OAuth
- Analytics/Search Console
- Cloud Storage/BigQuery not coupled to inference
- ADK framework code that can remain while only the model backend changes

For structured-output, embedding, and ADK worked examples, see
[examples.md](examples.md).
