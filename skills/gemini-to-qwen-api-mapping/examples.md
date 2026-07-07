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
    print(f"WARNING: Parse failed. Raw response prefix: {(resp.text or '')[:120]}")
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
    "You are an expert in analyzing multilingual YouTube comments."
    "\n\n"
    "Always respond only in valid JSON format."
    "Do not include any preamble, explanatory text, or Markdown code fences. "
    "Output only a single JSON object."
    "The output JSON object must strictly follow the following structure and types:\n"
    "{\n"
    '  "is_soccer_related": true or false,\n'
    '  "relevance_reason": "reason for the judgment",\n'
    '  "sentiment": {"positive": number, "negative": number, "neutral": number},\n'
    '  "positive_themes": [{"theme_ja": "Japanese string", "theme_en": "English string", "mention_count": integer}],\n'
    '  "negative_themes": [{"theme_ja": "Japanese string", "theme_en": "English string", "mention_count": integer}],\n'
    '  "quotable_comments": [{"original": "string", "translated_ja": "Japanese string", '
    '"translated_en": "English string", "author": "string", "likes": integer, '
    '"original_language": "language code"}],\n'
    '  "mentioned_teams": [{"team": "English national team name", '
    '"sentiment": "positive|neutral|negative", "mention_count": integer}]\n'
    "}\n"
    "Include all fields without omitting any of them."
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

## Example 3: ADK agent runtime migration

Source file:

```text
app/soccer_agent/agent.py
```

This example covers the web-app agent layer, not just offline pipeline scripts.

The reusable migration pattern has four parts:

1. Wrap the ADK model with `LiteLlm` for non-Gemini backends.
2. Replace Gemini query embeddings with DashScope OpenAI-compatible embeddings.
3. Keep the vector dimensionality and vector-index isolation explicit.
4. Avoid runtime package downloads in Function Compute by launching a bundled MCP server with `node`, not `npx`.

### Focused diff: imports, model selection, and environment variables

```diff
 import asyncio
-import json
 import math
 import os

-from google import genai
-from google.genai import types
+from openai import OpenAI
+from pymongo import AsyncMongoClient

 from google.adk.agents import Agent
+from google.adk.models.lite_llm import LiteLlm
 from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
 from mcp import StdioServerParameters
-from mcp.client.stdio import stdio_client
-from mcp import ClientSession

-DB_NAME = "soccertube"
-COLLECTION = "videos"
-VECTOR_INDEX = "video_semantic_index"
+DB_NAME = os.environ.get("SOCCER_DB_NAME", "soccertube")
+COLLECTION = os.environ.get("SOCCER_COLL_NAME", "videos")
+VECTOR_INDEX = os.environ.get("SOCCER_INDEX_NAME", "video_semantic_index")
 VECTOR_PATH = "embedding"
-EMBED_MODEL = "gemini-embedding-001"
-EMBED_DIM = 768
-AGENT_MODEL = "gemini-3.1-flash-lite"
+
+EMBED_MODEL = os.environ.get("QWEN_EMBED_MODEL", "text-embedding-v4")
+EMBED_DIM = 768
+DASHSCOPE_BASE_URL = os.environ.get(
+    "DASHSCOPE_BASE_URL",
+    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
+)
+
+os.environ.setdefault("DASHSCOPE_API_BASE", DASHSCOPE_BASE_URL)
+
+QWEN_CHAT_MODEL = os.environ.get("QWEN_CHAT_MODEL", "qwen3.7-max")
+AGENT_MODEL = LiteLlm(model=f"dashscope/{QWEN_CHAT_MODEL}")
```

### Why `LiteLlm` is required for ADK

In this project, `google.adk.agents.Agent` can still be kept as the agent framework.
The model value is the part that changes.

```python
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

# LiteLLM expects DASHSCOPE_API_BASE, while the OpenAI SDK client below uses
# base_url=DASHSCOPE_BASE_URL. Set both names so the two clients agree.
os.environ.setdefault("DASHSCOPE_API_BASE", DASHSCOPE_BASE_URL)

QWEN_CHAT_MODEL = os.environ.get("QWEN_CHAT_MODEL", "qwen3.7-max")
AGENT_MODEL = LiteLlm(model=f"dashscope/{QWEN_CHAT_MODEL}")

root_agent = Agent(
    model=AGENT_MODEL,
    name="soccer_agent",
    instruction=INSTRUCTION,
    tools=[search_videos, mongodb_mcp],
)
```

Important notes:

- Passing a plain string such as `"gemini-3.1-flash-lite"` to ADK means Gemini.
- Passing a plain string such as `"qwen-plus"` is not enough for this ADK path.
- Use `LiteLlm(model="dashscope/<model-name>")` for Qwen / DashScope models.
- Install `litellm` in the app runtime dependency group.
- Set `DASHSCOPE_API_KEY` for LiteLLM and the OpenAI-compatible embedding client.
- Set `DASHSCOPE_API_BASE` for LiteLLM and `DASHSCOPE_BASE_URL` for the OpenAI SDK, or bridge them with `os.environ.setdefault`.

### Focused diff: query embedding

Before, query embeddings used Gemini GenAI with `RETRIEVAL_QUERY`.

```python
from google import genai
from google.genai import types

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

_genai_client: genai.Client | None = None

def _client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client

def _embed_query_sync(query_text: str) -> list[float]:
    resp = _client().models.embed_content(
        model=EMBED_MODEL,
        contents=query_text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBED_DIM,
        ),
    )
    return _l2_normalize(list(resp.embeddings[0].values))
```

After, query embeddings use the DashScope OpenAI-compatible endpoint.

```python
from openai import OpenAI

EMBED_MODEL = os.environ.get("QWEN_EMBED_MODEL", "text-embedding-v4")
EMBED_DIM = 768

_dashscope_client: OpenAI | None = None

def _client() -> OpenAI:
    global _dashscope_client
    if _dashscope_client is None:
        _dashscope_client = OpenAI(
            api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
            base_url=DASHSCOPE_BASE_URL,
        )
    return _dashscope_client

def _embed_query_sync(query_text: str) -> list[float]:
    resp = _client().embeddings.create(
        model=EMBED_MODEL,
        input=query_text,
        dimensions=EMBED_DIM,
    )
    return _l2_normalize(list(resp.data[0].embedding))
```

Key migration notes:

- Preserve `EMBED_DIM = 768` if the existing Atlas Vector Search index is 768-dimensional.
- Re-embed the stored corpus with the same Qwen embedding model before using Qwen query embeddings.
- Do not query a Gemini-generated vector index with Qwen-generated query vectors unless you are explicitly testing degraded cross-model retrieval.
- The DashScope OpenAI-compatible endpoint does not expose Gemini's `task_type="RETRIEVAL_QUERY"` option. If asymmetric query/document embeddings are required, evaluate the native DashScope SDK separately.

### Focused diff: vector search execution path

The Gemini/GCP version embedded the query in code, then called MongoDB MCP `aggregate`.
That preserved MCP involvement, but it required parsing MCP output and starting an MCP process inside every vector-search call.

```diff
-# --- Robust parsing of MCP aggregate results ---
-def _parse_aggregate_result(result) -> tuple[list | None, str]:
-    ...
-
-# --- Custom tool: semantic search (embed -> code directly calls MCP aggregate) ---
+# --- MongoDB (pymongo Async API; direct connection only for $vectorSearch) ----
+_mongo_client: AsyncMongoClient | None = None
+
+def _get_client() -> AsyncMongoClient:
+    global _mongo_client
+    if _mongo_client is None:
+        _mongo_client = AsyncMongoClient(os.environ.get("MONGODB_URI", ""))
+    return _mongo_client
+
+def _get_collection():
+    return _get_client()[DB_NAME][COLLECTION]
+
+# --- Custom tool: semantic search (embed -> direct pymongo $vectorSearch) ------
 async def search_videos(...):
     query_vector = await asyncio.to_thread(_embed_query_sync, query_text)
     pipeline = [{"$vectorSearch": vsearch}, {"$project": PROJECTION}]

-    # Start the official MongoDB MCP and call aggregate within this tool call.
-    result = None
     try:
-        async with stdio_client(_mcp_server_params()) as (read, write):
-            async with ClientSession(read, write) as session:
-                await session.initialize()
-                result = await session.call_tool(
-                    "aggregate",
-                    {
-                        "database": DB_NAME,
-                        "collection": COLLECTION,
-                        "pipeline": pipeline,
-                    },
-                )
+        cursor = await _get_collection().aggregate(pipeline)
+        videos = [doc async for doc in cursor]
     except Exception as e:
-        if result is None:
-            return {"error": f"mcp aggregate failed: {e}", "count": 0, "videos": []}
+        return {"error": f"aggregate failed: {e}", "count": 0, "videos": []}

-    parsed, raw = _parse_aggregate_result(result)
-    if parsed is not None:
-        return {"count": len(parsed), "videos": parsed}
-    return {"count": 0, "videos": [], "raw": raw[:4000]}
+    return {"count": len(videos), "videos": videos}
```

This is not a universal requirement for Gemini → Qwen migration, but it is a useful pattern for RAG tools:

- Keep the LLM away from raw embedding vectors.
- Keep semantic search as one custom tool: `query_text -> embedding -> $vectorSearch -> projected docs`.
- Use MCP for detail lookup, count, and schema inspection, while keeping high-volume vector search in ordinary application code.
- Remove MCP result parsing code when vector search no longer goes through MCP.

### Focused diff: MCP startup on Alibaba Cloud Function Compute

The original app used `npx` to start the official MongoDB MCP server.

```python
def _mcp_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="npx",
        args=["-y", "mongodb-mcp-server", "--readOnly"],
        env={
            **os.environ,
            "MDB_MCP_CONNECTION_STRING": os.environ.get("MONGODB_URI", ""),
            "MDB_MCP_TELEMETRY": "disabled",
        },
    )
```

The migrated app starts the MCP server from the deployment artifact instead.

```python
_MONGODB_MCP_ENTRY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "node_modules",
    "mongodb-mcp-server",
    "dist",
    "esm",
    "index.js",
)

def _mcp_server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="node",
        args=[_MONGODB_MCP_ENTRY, "--readOnly"],
        env={
            **os.environ,
            "MDB_MCP_CONNECTION_STRING": os.environ.get("MONGODB_URI", ""),
            "MDB_MCP_TELEMETRY": "disabled",
            "HOME": "/tmp",
            "MDB_MCP_LOG_PATH": "/tmp/mongodb-mcp-logs",
            "MDB_MCP_EXPORTS_PATH": "/tmp/mongodb-mcp-exports",
        },
    )
```

Build-time packaging pattern:

```bash
npm install --prefix build mongodb-mcp-server
rm -rf build/node_modules/@oven
```

Important notes:

- Do not use `npx` as the production startup path on disposable serverless runtimes.
- Do not download runtime packages during Function Compute startup.
- Bundle `mongodb-mcp-server` into the deployment artifact under `node_modules/`.
- Keep the Node.js 20 Function Compute public layer attached so the `node` executable exists.
- Always merge `os.environ` into the MCP server env; replacing it can remove `PATH` and make `node` unavailable.
- Set writable MCP paths under `/tmp`, because `/opt` and default home directories may not be writable.

### Focused diff: MCP tool instruction after DB names become configurable

When `DB_NAME`, `COLLECTION`, and `VECTOR_INDEX` become environment-variable driven,
the model instruction should explicitly tell the LLM to pass database and collection
arguments to the MCP tools.

```diff
-- **find / count**: USE THESE to fetch specific documents by exact fields.
+- There is no tool named find_videos anymore. For fetching specific documents,
+  counting, or inspecting structure, use the official MongoDB MCP tools:
+  **find**, **count**, **list-collections**, **collection-schema**. These tools
+  are NOT bound to a fixed database/collection, so you MUST always pass
+  database="{DB_NAME}" and collection="{COLLECTION}" explicitly — forgetting
+  this may silently query the wrong database or collection.
```

This matters because the Qwen deployment may use `SOCCER_DB_NAME=qwen-soccertube`,
while the Gemini deployment may continue to use the original `soccertube` database.

### Environment

```bash
pip install openai litellm pymongo google-adk mcp
export DASHSCOPE_API_KEY="..."
export DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
export DASHSCOPE_API_BASE="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
export QWEN_CHAT_MODEL="qwen3.7-max"
export QWEN_EMBED_MODEL="text-embedding-v4"

# Use a separate DB or collection after re-embedding to avoid mixed vector spaces.
export SOCCER_DB_NAME="qwen-soccertube"
export SOCCER_COLL_NAME="videos"
export SOCCER_INDEX_NAME="video_semantic_index"
```

### Important migration notes

- This file is an app runtime migration, so it touches more than the bare LLM SDK call.
- The ADK framework can remain; the model object changes to `LiteLlm`.
- Embeddings and chat completion use different client layers: OpenAI SDK for embeddings, LiteLLM for ADK chat model routing.
- The vector-search collection should be separated from the Gemini collection after re-embedding.
- The MCP server remains useful, but runtime startup must be serverless-safe.
- This pattern belongs partly to `gemini-to-qwen-api-mapping` and partly to deployment guidance. Keep the API mapping example here, and cross-link deployment-specific packaging details from `deploy-alibaba-fc-advisor` if the project has that skill.

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
                    "You are an expert in JSON formatting."
                    "Repair the broken JSON string into valid JSON format."
                    "Output only a single JSON object."
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
| `gemini-3.1-flash-lite` | `qwen-plus`, `qwen3.7-max`, or another DashScope chat model |
| Plain ADK model string for Gemini | `LiteLlm(model="dashscope/<model-name>")` for Qwen |
| Google GenAI SDK | OpenAI SDK with DashScope compatible base URL |
| `response_schema=PydanticModel` | `response_format={"type": "json_object"}` + local Pydantic validation |
| Fixed `soccertube` vector DB | Separate Qwen vector DB/collection, e.g. `SOCCER_DB_NAME=qwen-soccertube` |
| `npx mongodb-mcp-server` at runtime | Bundled `node_modules` + direct `node <index.js>` startup |

Recommended Qwen environment variables:

```bash
export DASHSCOPE_API_KEY="..."
export DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
export QWEN_EMBED_MODEL="text-embedding-v4"
export QWEN_CHAT_MODEL="qwen-plus"
export QWEN_FIX_MODEL="qwen-flash"

# For ADK + LiteLLM in the app runtime:
export DASHSCOPE_API_BASE="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# For app/runtime RAG isolation after Qwen re-embedding:
export SOCCER_DB_NAME="qwen-soccertube"
export SOCCER_COLL_NAME="videos"
export SOCCER_INDEX_NAME="video_semantic_index"
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

For SoccerScope pipeline demo scope, the intended code-edit targets are:

```text
pipeline/1_embed_videos.py
pipeline/3_analyze_comments.py
```

For full app runtime migration, `app/soccer_agent/agent.py` is also an intended edit target because it contains the ADK model selection, query embedding path, vector-search tool, and MCP startup path.

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
