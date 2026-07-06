# Worked examples: Gemini SDK → Qwen Cloud / DashScope OpenAI-compatible API

This file contains concrete migration examples from the SoccerScope demo.

The goal is not to copy the entire project-specific diff, but to preserve reusable API
migration patterns:

- Gemini embeddings → Qwen/DashScope embeddings
- Gemini `response_schema=PydanticModel` → Qwen JSON mode + local validation
- `GEMINI_API_KEY` → `DASHSCOPE_API_KEY`
- Google SDK client → OpenAI-compatible DashScope client

---

## Example 1: Embeddings

Source file:

```text
pipeline/1_embed_videos.py
```

### Before: Gemini embedding

```python
from google import genai
from google.genai import types

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
CHUNK_SIZE = 20

client = genai.Client()

result = client.models.embed_content(
    model=EMBED_MODEL,
    contents=texts,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=EMBED_DIM,
    ),
)

return [normalize(e.values) for e in result.embeddings]
```

Environment:

```bash
pip install google-genai numpy
export GEMINI_API_KEY="..."
```

### After: Qwen/DashScope embedding via OpenAI-compatible API

```python
from openai import OpenAI

EMBED_MODEL = os.environ.get("QWEN_EMBED_MODEL", "text-embedding-v4")
EMBED_DIM = 768
CHUNK_SIZE = 10

DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

client = OpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=DASHSCOPE_BASE_URL,
)

result = client.embeddings.create(
    model=EMBED_MODEL,
    input=texts,
    dimensions=EMBED_DIM,
)

# Preserve the original input order before attaching embeddings back to records.
ordered = sorted(result.data, key=lambda e: e.index)
return [normalize(e.embedding) for e in ordered]
```

Environment:

```bash
pip install openai numpy
export DASHSCOPE_API_KEY="..."
```

### Important migration notes

- `gemini-embedding-001` is replaced with `text-embedding-v4`.
- Keep `EMBED_DIM = 768` if the existing MongoDB Atlas Vector Search index expects 768 dimensions.
- Gemini supports `task_type="RETRIEVAL_DOCUMENT"` through `EmbedContentConfig`.
- DashScope OpenAI-compatible embeddings do not expose the same `task_type` parameter.
- If document/query asymmetric embedding is required later, check DashScope native SDK options such as `text_type="document"` / `text_type="query"` instead of the OpenAI-compatible API.
- Qwen `text-embedding-v4` has a smaller safe batch size in this demo, so `CHUNK_SIZE` was changed from `20` to `10`.
- Do not mix Gemini-generated vectors and Qwen-generated vectors in the same vector index unless the retrieval quality impact is explicitly evaluated.

---

## Example 2: Structured JSON analysis

Source file:

```text
pipeline/3_analyze_comments.py
```

### Before: Gemini structured output with Pydantic response_schema

Gemini can directly use a Pydantic model as `response_schema`.

```python
from pydantic import BaseModel
from google import genai
from google.genai import types

MODEL = "gemini-3.1-flash-lite"

class CommentAnalysis(BaseModel):
    is_soccer_related: bool
    relevance_reason: str
    sentiment: Sentiment
    positive_themes: list[Theme]
    negative_themes: list[Theme]
    quotable_comments: list[QuotableComment]
    mentioned_teams: list[MentionedTeam]

client = genai.Client()

resp = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=CommentAnalysis,
        temperature=TEMPERATURE,
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

parsed = resp.parsed
if parsed is None:
    print(f"WARNING: パース失敗。生応答先頭: {(resp.text or '')[:120]}")
    return None

return parsed
```

Environment:

```bash
pip install google-genai pydantic
export GEMINI_API_KEY="..."
```

### After: Qwen/DashScope JSON mode + local Pydantic validation

DashScope OpenAI-compatible API does not enforce a Pydantic schema like Gemini
`response_schema`.

Use three layers instead:

1. Ask for JSON explicitly in the system prompt.
2. Use `response_format={"type": "json_object"}`.
3. Validate the returned JSON locally with Pydantic.

```python
import json
from pydantic import BaseModel, ValidationError
from openai import OpenAI

MODEL = os.environ.get("QWEN_CHAT_MODEL", "qwen-plus")
FIX_MODEL = os.environ.get("QWEN_FIX_MODEL", "qwen-flash")

DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

TIMEOUT_SECONDS = float(os.environ.get("QWEN_TIMEOUT_SECONDS", "60"))

class CommentAnalysis(BaseModel):
    is_soccer_related: bool
    relevance_reason: str
    sentiment: Sentiment
    positive_themes: list[Theme]
    negative_themes: list[Theme]
    quotable_comments: list[QuotableComment]
    mentioned_teams: list[MentionedTeam]

client = OpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=DASHSCOPE_BASE_URL,
    timeout=TIMEOUT_SECONDS,
)
```

The system instruction should explicitly contain the word `JSON` / `json` and the expected schema.

```python
SYSTEM_INSTRUCTION = (
    "あなたは多言語のYouTubeコメントを分析する専門家です。"
    "\n\n"
    "必ず有効なJSON形式のみで応答してください。"
    "前置き・説明文・マークダウンのコードブロックは一切付けず、"
    "JSONオブジェクト単体を出力してください。"
    "出力するJSONオブジェクトは、以下の構造・型に厳密に従ってください:\n"
    "{\n"
    '  "is_soccer_related": true または false,\n'
    '  "relevance_reason": "判定理由",\n'
    '  "sentiment": {"positive": 数値, "negative": 数値, "neutral": 数値},\n'
    '  "positive_themes": [{"theme_ja": "文字列", "theme_en": "文字列", "mention_count": 整数}],\n'
    '  "negative_themes": [{"theme_ja": "文字列", "theme_en": "文字列", "mention_count": 整数}],\n'
    '  "quotable_comments": [{"original": "文字列", "translated_ja": "文字列", '
    '"translated_en": "文字列", "author": "文字列", "likes": 整数, '
    '"original_language": "言語コード"}],\n'
    '  "mentioned_teams": [{"team": "英語の代表チーム名", '
    '"sentiment": "positive|neutral|negative", "mention_count": 整数}]\n'
    "}\n"
    "全てのフィールドは省略せず必ず含めてください。"
)
```

Call Qwen in JSON mode.

```python
def call_json(client: OpenAI, prompt: str):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=TEMPERATURE,
        # Required for hybrid-thinking models when using JSON mode.
        # Harmless for models where thinking is already disabled by default.
        extra_body={"enable_thinking": False},
    )
```

Parse and validate locally.

```python
def analyze_with_retry(client: OpenAI, prompt: str):
    try:
        resp = call_json(client, prompt)
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        return CommentAnalysis(**data), None

    except json.JSONDecodeError as e:
        return None, f"json_decode_error:{str(e)[:120]}"

    except ValidationError as e:
        return None, f"schema_validation_error:{str(e)[:120]}"

    except Exception as e:
        return None, f"api_error:{str(e)[:120]}"
```

Environment:

```bash
pip install openai pydantic python-dotenv
export DASHSCOPE_API_KEY="..."
```

### Important migration notes

- Gemini `response_schema=CommentAnalysis` is a schema-enforced structured output path.
- DashScope OpenAI-compatible `response_format={"type": "json_object"}` guarantees JSON syntax, not full Pydantic schema compliance.
- Therefore, always validate the returned object with the local Pydantic model.
- Include the word `json` / `JSON` in the prompt when using `response_format={"type": "json_object"}`.
- Do not wrap the JSON output in Markdown code fences.
- Do not set a hard `max_tokens` / `max_output_tokens` cap for structured output unless necessary, because truncation can corrupt JSON.
- Do not combine thinking mode with JSON mode. Pass `extra_body={"enable_thinking": False}` when using DashScope through the OpenAI SDK.
- Set an explicit timeout. The OpenAI SDK default timeout can be too long for batch pipelines.

---

## Optional hardening used in the SoccerScope migration

The SoccerScope demo added several production-oriented safeguards around the core API migration.
These are useful, but they are not required for every project.

### Retry transient errors

```python
def is_retryable_transient_error(msg: str) -> bool:
    lowered = msg.lower()
    return (
        "429" in msg
        or "resource_exhausted" in lowered
        or "throttling" in lowered
        or "timed out" in lowered
        or "timeout" in lowered
        or "connection" in lowered
    )
```

### Do not retry content moderation failures blindly

```python
def is_content_moderation_error(msg: str) -> bool:
    lowered = msg.lower()
    return (
        "inappropriate content" in lowered
        or "datainspectionfailed" in lowered
        or "data_inspection_failed" in lowered
        or "content_filter" in lowered
    )
```

### Use a cheap model to repair malformed JSON only when needed

```python
def repair_json(client: OpenAI, broken_text: str) -> str:
    resp = client.chat.completions.create(
        model=FIX_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたはJSON形式の専門家です。"
                    "壊れたJSON文字列を有効なJSON形式に修復してください。"
                    "JSONオブジェクト単体のみを出力してください。"
                ),
            },
            {"role": "user", "content": broken_text},
        ],
        response_format={"type": "json_object"},
        extra_body={"enable_thinking": False},
    )
    return resp.choices[0].message.content
```

---

## Environment variable mapping

| Gemini / GCP side | Qwen / Alibaba Cloud side |
|---|---|
| `GEMINI_API_KEY` | `DASHSCOPE_API_KEY` |
| `gemini-embedding-001` | `text-embedding-v4` |
| `gemini-3.1-flash-lite` | `qwen-plus` or another DashScope chat model |
| Google GenAI SDK | OpenAI SDK with DashScope compatible base URL |
| `response_schema=PydanticModel` | `response_format={"type": "json_object"}` + local Pydantic validation |

Recommended Qwen environment variables:

```bash
export DASHSCOPE_API_KEY="..."
export DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
export QWEN_EMBED_MODEL="text-embedding-v4"
export QWEN_CHAT_MODEL="qwen-plus"
export QWEN_FIX_MODEL="qwen-flash"
```

---

## Anti-patterns

Do not blindly rewrite every Google-related import.

For example, these are usually not part of a Gemini → Qwen LLM migration:

- YouTube Data API clients
- Google OAuth for unrelated services
- Google Search Console / Analytics clients
- BigQuery / Cloud Storage usage that is not directly tied to Gemini inference

Only rewrite files that actually call Gemini / Google GenAI / Vertex AI model APIs.

For SoccerScope demo scope, the intended code-edit targets are:

```text
pipeline/1_embed_videos.py
pipeline/3_analyze_comments.py
```

The following files are validation or data-flow context, but should not be edited for the minimal demo unless grep shows direct Gemini usage:

```text
pipeline/2_load_to_mongo.py
pipeline/4_load_comment_analysis.py
pipeline/phase2_collect_video_ids.py
pipeline/phase3_fetch_metadata.py
pipeline/phase4_fetch_comments.py
pipeline/phase7_calc_buzz_score.py
pipeline/build_stats_page.py
```
