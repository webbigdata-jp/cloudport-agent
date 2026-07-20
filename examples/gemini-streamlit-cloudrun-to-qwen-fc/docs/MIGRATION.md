# Migration notes: Gemini Streamlit / Cloud Run → Qwen / Alibaba Cloud FC

Updated: **2026-07-20**

## Scope

Source:

- Google Cloud Gemini multimodal Streamlit sample
- Gemini API / Vertex AI
- Cloud Run deployment pattern

Target:

- Alibaba Cloud Model Studio OpenAI-compatible API
- Qwen text/image/video models
- Alibaba Cloud Function Compute Web Function using a Custom Runtime ZIP

The Streamlit UI remains close to the source application. Provider-specific
request conversion is localized in `cloudport_compat.py`.

## Model selection

The model IDs in `app.py` are example defaults, not a permanent equivalence
table. Model availability and multimodal support must be checked in the target
Model Studio region/workspace before deployment.

Because this sample uses one global selector for text, image, and video tabs,
every model exposed by that selector must support all modalities used by the
application. A production migration should normally choose a model per call
site rather than mechanically translating one source ID to one target ID.

## Compatibility layer

`cloudport_compat.py` mirrors only the Google Gen AI surface required by this
sample:

- `Part.from_uri(...)`
- `GenerateContentConfig`
- `ThinkingConfig`
- `client.models.generate_content(...)`
- response `.text`

| Gemini-style input | Qwen / OpenAI-compatible request |
|---|---|
| plain string | user message containing a text part |
| image URI | `image_url` content part |
| video URI | `video_url` content part plus `fps` |
| `max_output_tokens` | `max_completion_tokens` |
| positive thinking budget | `extra_body.enable_thinking=true` and `thinking_budget` |
| thinking budget `0` | `extra_body.enable_thinking=false` |
| temperature at Gemini maximum | clamped below Qwen's exclusive upper bound |

`max_completion_tokens` covers reasoning and the final answer. For manual
thinking, the compatibility layer adds the requested answer budget, thinking
budget, and a small accounting margin.

## Endpoint resolution

Resolution order:

1. `DASHSCOPE_BASE_URL`
2. `DASHSCOPE_REGION` plus `DASHSCOPE_WORKSPACE_ID`
3. international fallback endpoint

For production, prefer an explicit workspace-scoped `DASHSCOPE_BASE_URL`. The
API key and endpoint must belong to the same region/workspace.

## Application defects fixed during migration

The migration also fixes defects in the supplied/upstream-style app:

1. ER diagram output was generated but not rendered.
2. Glasses comparison sent the ER diagram instead of the glasses images.
3. A multimodal content list was accidentally nested.
4. Furniture reused an unrelated stale config object.
5. Image/video requests did not consistently apply the selected thinking mode.
6. Empty responses could be passed to `st.markdown`.

These fixes are important evidence for the CloudPort Agent validation skill:
provider migration testing must validate actual payloads and rendered output,
not merely successful imports.

## Function Compute packaging

`deploy.sh`:

- requires Linux x86_64; WSL2 is acceptable;
- creates a Python 3.12 build environment;
- installs dependencies directly at the ZIP root;
- copies only `app.py`, `cloudport_compat.py`, and optional Streamlit config;
- generates a root-level executable `bootstrap`;
- binds Streamlit to `0.0.0.0:${FC_CUSTOM_LISTEN_PORT:-9000}`;
- sets writable `HOME=/tmp` by default;
- validates required and forbidden root entries;
- removes temporary build directories unless `KEEP_BUILD_DIR=1`.

The script does not truly cross-compile wheels on native macOS or Windows.
Running it under WSL2 works because the build host presented to pip is Linux
x86_64.

## Environment variables

Required:

```bash
DASHSCOPE_API_KEY=...
```

Recommended:

```bash
DASHSCOPE_BASE_URL=https://<workspace-id>.<region>.maas.aliyuncs.com/compatible-mode/v1
QWEN_TIMEOUT_SECONDS=180
```

Resolver alternative:

```bash
DASHSCOPE_REGION=tokyo
DASHSCOPE_WORKSPACE_ID=<workspace-id>
```

Function Compute supplies `FC_CUSTOM_LISTEN_PORT`; `FC_FUNCTION_NAME` may also
be present and is used only to adjust the UI.

## Account-dependent checks

The following cannot be established by offline unit tests:

- model availability in the selected region/workspace;
- remote image/video accessibility from Model Studio;
- latency with Auto/Manual thinking;
- FC memory, timeout, ZIP-size, and cold-start behavior;
- public URL and authentication settings.

Use `smoke_test.py` with its Alibaba-hosted media defaults before testing the
Google-hosted demonstration assets embedded in the Streamlit app.
