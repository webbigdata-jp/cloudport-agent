---
name: project-soccerscope
description: Migration Project Profile for SoccerScope, a YouTube soccer-video analytics pipeline and web search agent. Use when migrating, editing, validating, or demoing SoccerScope Gemini/GCP to Qwen Cloud/Alibaba Cloud migration, especially pipeline scripts, soccer_agent, or app deployment.
paths:
  - "pipeline/**"
  - "app/**"
---

# Project Profile: SoccerScope

This is a project-specific profile for the SoccerScope migration demo.
Keep project-specific scope, file boundaries, and execution order here.
Keep generic Gemini → Qwen API conversion know-how in the core skills such as
`gemini-to-qwen-api-mapping`, `dependency-migration`, `migration-validation`,
and `deploy-alibaba-fc-advisor`.

## Migration mode selection

Before editing, determine which scope the user wants.

### Demo scope: minimal CloudPort video demo

Use this scope when the user wants a short demo showing that a GCP/Gemini-based
pipeline can be automatically migrated to Alibaba Cloud/Qwen with human approval.

The intended demo flow is:

1. Skill loads.
2. Qwen Code proposes a plan.
3. Qwen Code edits exactly two code files.
4. Human approves the file rewrite/diff.
5. `migration-validation` runs checks or proposes the validation checklist.
6. `deploy-alibaba-fc-advisor` provides human-executed Alibaba Cloud deployment advice.

#### Demo code-edit targets

Edit only these two files in the minimal demo unless the user explicitly expands scope:

| File | Gemini usage | Qwen mapping |
|---|---|---|
| `pipeline/1_embed_videos.py` | `models.embed_content` / Gemini embedding | DashScope OpenAI-compatible `client.embeddings.create` with `text-embedding-v4` |
| `pipeline/3_analyze_comments.py` | `models.generate_content` + Pydantic `response_schema` | DashScope OpenAI-compatible `chat.completions.create` + JSON mode + local Pydantic validation |

## Dependency file layout (do not guess)

| Component | Dependency file | Manager | Why |
|---|---|---|---|
| `pipeline/**` | `pipeline/pyproject.toml` + `pipeline/uv.lock` | uv | Local batch environment |
| `app/**` | `app/requirements.txt` | pip | FC console zip upload — deps must be vendored into the zip, which the uv workflow does not produce |

There is NO `pipeline/requirements.txt` and NO `app/pyproject.toml`.
Never look for or create dependency files other than the two above.

#### Demo dependency/config handling

For the minimal video demo, do not edit dependency files unless the user explicitly asks.
Instead, report required follow-up changes during validation.

Likely follow-up items:

- Replace `google-genai` with `openai` in the relevant pipeline dependency file.
- Ensure `python-dotenv`, `numpy`, and `pydantic` are present as needed.
- Set `DASHSCOPE_API_KEY`.
- Set optional model variables such as `QWEN_EMBED_MODEL`, `QWEN_CHAT_MODEL`, and `QWEN_FIX_MODEL`.

If the user asks for a fully runnable local branch, then `dependency-migration` may update:

- `pipeline/pyproject.toml`
- `pipeline/uv.lock`
- `.env.example` or project-specific environment documentation, if present

### Full migration scope: complete SoccerScope migration

Use this scope when the user asks to migrate the whole SoccerScope repo, app, or search agent,
or when the user says the goal is no longer just the minimal video demo.

#### Full code-change candidates

Only edit these if grep confirms direct Gemini / Google GenAI / Vertex AI / ADK model usage
or Gemini-specific configuration:

| File | Role | Edit condition |
|---|---|---|
| `pipeline/1_embed_videos.py` | video metadata embeddings | Direct Gemini embedding usage |
| `pipeline/3_analyze_comments.py` | comment analysis and structured JSON | Direct Gemini generation / `response_schema` usage |
| `app/soccer_agent/agent.py` | web search agent brain | Gemini, Vertex, Google ADK model config, or Gemini tool-calling loop exists |
| `app/main.py` | app entrypoint | Gemini-specific env/config/model wiring exists |
| `app/static/index.html` | frontend | Gemini/GCP branding, endpoint assumptions, or demo copy must change |
| dependency/config files | runtime dependencies and env vars | Required for runnable Qwen branch |

Always inspect before editing. Do not assume all `app/**` files need changes.

#### Full validation targets

These files/scripts are part of the end-to-end data flow and should be included in validation,
even when they are not edited:

- `pipeline/1_embed_videos.py`
- `pipeline/2_load_to_mongo.py`
- `pipeline/3_analyze_comments.py`
- `pipeline/4_load_comment_analysis.py`
- `app/main.py`
- `app/soccer_agent/agent.py`
- `app/static/index.html`

## Explicit non-targets

Do not edit these files during the minimal demo.
In full migration, edit them only if grep shows direct Gemini / Google GenAI / Vertex model usage.

- `pipeline/phase2_collect_video_ids.py` — YouTube video ID collection.
- `pipeline/phase3_fetch_metadata.py` — YouTube metadata fetch.
- `pipeline/phase4_fetch_comments.py` — YouTube comment fetch.
- `pipeline/phase7_calc_buzz_score.py` — buzz-score calculation.
- `pipeline/2_load_to_mongo.py` — MongoDB loader for embedded video metadata.
- `pipeline/4_load_comment_analysis.py` — MongoDB loader for comment analysis.
- `pipeline/build_stats_page.py` — stats page generation; Gemini may be optional. Leave out of minimal demo.

Important: do not blindly rewrite every Google-related import.
`google-api-python-client` usage for the YouTube Data API is not a Gemini/Qwen migration target.

## Required pre-edit grep

Before changing files, run or propose searches for:

```bash
grep -RIn "google.genai\|google-generativeai\|genai.Client\|generate_content\|embed_content\|response_schema\|GEMINI_API_KEY\|GOOGLE_GENAI_USE_VERTEXAI\|Vertex\|Gemini\|gemini-" pipeline app
```

Use the grep result to confirm whether the task is demo scope or full migration scope.

## Configuration conventions

### Environment variables

Map Gemini/GCP variables to Qwen/DashScope variables:

| Gemini / GCP | Qwen / Alibaba Cloud |
|---|---|
| `GEMINI_API_KEY` | `DASHSCOPE_API_KEY` |
| `gemini-embedding-001` | `text-embedding-v4` |
| Gemini chat model | `QWEN_CHAT_MODEL`, usually `qwen-plus` for this demo |
| Optional JSON repair model | `QWEN_FIX_MODEL`, usually `qwen-flash` |
| Google GenAI SDK | OpenAI SDK with DashScope compatible base URL |

Default DashScope OpenAI-compatible base URL:

```text
https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

Use `DASHSCOPE_BASE_URL` to override it.

### `.env` location

The original Gemini pipeline may load environment variables from `app/soccer_agent/.env`.
For the isolated Qwen pipeline demo, it is acceptable for migrated pipeline scripts to load
`pipeline/.env` via `load_dotenv(SCRIPT_DIR / '.env')`.

Do not introduce hardcoded absolute paths or old local paths such as `git/...`.

## Data-store cautions

SoccerScope uses MongoDB Atlas.

Vector-search caution:

- Gemini vectors and Qwen vectors should not be mixed in the same corpus/index without explicit evaluation.
- Keep embedding dimensions aligned with the MongoDB Atlas Vector Search index.
- The demo keeps `EMBED_DIM = 768` to match the existing index assumption.
- If the provider/model changes, recreate or separate the vector index as needed.

Recommended demo separation:

- Use a separate DB name such as `qwen-soccertube` via `SOCCER_DB_NAME` when loading migrated outputs.
- The embedding script itself does not need to know the DB name if DB loading is handled by `2_load_to_mongo.py`.

## Execution order

Daily pipeline order:

```text
run_daily.sh
→ phase2_collect_video_ids.py
→ phase3_fetch_metadata.py
→ phase4_fetch_comments.py
→ phase7_calc_buzz_score.py
→ 1_embed_videos.py
→ 2_load_to_mongo.py
→ 3_analyze_comments.py
→ 4_load_comment_analysis.py
→ build_stats_page.py
```

Pipeline scripts assume `cwd == pipeline/` unless the script has been explicitly refactored.
Preserve this invariant unless the user asks for broader cleanup.

## Validation expectations

After editing the demo files, use `migration-validation`.
At minimum, check:

- Imports resolve.
- `DASHSCOPE_API_KEY` missing produces a clear error.
- The scripts can locate their date-based input files or fail with clear instructions.
- Embedding output still contains normalized 768-dimensional vectors.
- Comment-analysis output validates against the local Pydantic model.
- No phase2/phase3/phase4/phase7 files were modified in the minimal demo.

For full migration, additionally check:

- Web app starts locally.
- Agent uses Qwen/DashScope rather than Gemini.
- Frontend copy and backend endpoint expectations are consistent.
- MongoDB loader scripts can ingest Qwen-generated outputs.

## Deployment

### What runs where

| Component | Where it runs | Deployment method |
|---|---|---|
| `app/**` (soccer_agent web app) | Alibaba Cloud Function Compute | Console **zip upload** of the code package. No Docker, no ACR, no `s` CLI in the current workflow. |
| `pipeline/**` (batch scripts) | **Local machine** via `run_daily.sh` (true for both the Gemini and Qwen versions) | Not deployed to the cloud at all. |

### Consequences for deployment advice

- Demo scope (only `pipeline/1_embed_videos.py` and
  `pipeline/3_analyze_comments.py` changed): **no FC redeploy is
  required**. The only follow-ups are local: install `openai`
  (replacing `google-genai`) in the pipeline environment and set
  `DASHSCOPE_API_KEY` (plus optional `QWEN_*` model variables).
- FC deployment steps apply only when `app/**` changes. In that case:
  build a self-contained zip of the app code package (all dependencies
  bundled; no runtime `pip`/`npx` fetches — FC cold-start timeouts
  forbid them), upload via the FC console, and set environment
  variables in the FC function configuration, not in the package.

Do not execute deployment commands automatically during the demo.
Use `deploy-alibaba-fc-advisor` to provide a checklist and human-executed steps.

The advisor should stop before destructive or cloud-mutating actions unless the user explicitly asks
and the normal approval flow is shown.
