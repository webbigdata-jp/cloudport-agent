# Test and deployment procedure

Run the stages in order so failures are isolated before Function Compute
upload.

## 1. Prerequisites

Local application tests:

- Python 3.11 or newer
- `pip`

Function Compute ZIP build:

- Linux x86_64 or WSL2 on x86_64
- `uv`, `zip`, and `unzip`
- Python 3.12 available to `uv`

Live tests:

- Model Studio API key
- endpoint in the same region/workspace as the key

Create a local environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 2. Offline checks

```bash
python -m compileall -q app.py cloudport_compat.py smoke_test.py tests
python -m unittest discover -s tests -v
bash -n deploy.sh
```

The unit tests cover URI part conversion, nested content flattening, endpoint
resolution, temperature clamping, `max_completion_tokens`, thinking
Auto/Manual/Off mapping, and response text extraction.

## 3. Configure Model Studio

Preferred:

```bash
export DASHSCOPE_API_KEY='...'
export DASHSCOPE_BASE_URL='https://<workspace-id>.<region>.maas.aliyuncs.com/compatible-mode/v1'
```

Resolver alternative for Tokyo:

```bash
export DASHSCOPE_API_KEY='...'
export DASHSCOPE_REGION='tokyo'
export DASHSCOPE_WORKSPACE_ID='<workspace-id>'
```

Do not combine a key and endpoint from different regions/workspaces.

## 4. API smoke tests

```bash
python smoke_test.py --mode text
python smoke_test.py --mode image
python smoke_test.py --mode video
```

Or:

```bash
python smoke_test.py --mode all
```

Expected output contains one `[PASS]` line for each requested modality.

| Symptom | Likely cause | First action |
|---|---|---|
| 401 / invalid key | missing or mismatched key | verify key and endpoint pair |
| 404 / model not found | model unavailable in workspace | override the smoke-test model |
| text passes, media fails | capability or remote fetch issue | use the default Alibaba-hosted media |
| Auto thinking times out | long non-streaming reasoning | try Off or Manual 4096 |
| parameter-related 400 | unsupported model/parameter combination | inspect the response body and retry defaults |

## 5. Local Streamlit acceptance

```bash
streamlit run app.py
```

Minimum matrix:

- Freeform with Thinking Auto, Manual, and Off
- one short story
- one marketing campaign
- furniture, oven, ER diagram, glasses, and math image tabs
- description, tags, highlights, and geolocation video tabs

Pass criteria:

- no terminal traceback;
- every clicked action renders non-empty output;
- ER output is visible;
- glasses requests use the glasses images;
- Thinking Off succeeds without sending `thinking_budget=0`.

## 6. Validate the manifest, then build and inspect `code.zip`

Offline source/host check:

```bash
CHECK_ONLY=1 ./deploy.sh
```

Full dependency build:

```bash
./deploy.sh
unzip -Z1 code.zip | sed -n '1,80p'
```

Required ZIP-root entries:

```text
app.py
cloudport_compat.py
bootstrap
```

Runtime packages such as `streamlit/` and `openai/` must also be present.
Development files such as `README.md`, `smoke_test.py`, `tests/`, and
`deploy.sh` are intentionally absent.

The script rejects native macOS/Windows hosts. Use WSL2 or another Linux x86_64
environment.

## 7. Local FC-like startup

```bash
rm -rf /tmp/cloudport-fc-test
mkdir -p /tmp/cloudport-fc-test
unzip -q code.zip -d /tmp/cloudport-fc-test
cd /tmp/cloudport-fc-test

export DASHSCOPE_API_KEY='...'
export DASHSCOPE_BASE_URL='https://<workspace-id>.<region>.maas.aliyuncs.com/compatible-mode/v1'
export FC_CUSTOM_LISTEN_PORT=9000
./bootstrap
```

In another terminal:

```bash
curl -fsS http://127.0.0.1:9000/_stcore/health
```

Expected response:

```text
ok
```

## 8. Function Compute deployment

Create or update a Web Function with a Python 3.12-compatible Custom Runtime:

1. Upload `code.zip`.
2. Leave the startup command empty; `bootstrap` is at the ZIP root.
3. Configure `DASHSCOPE_API_KEY` and `DASHSCOPE_BASE_URL`.
4. Allow outbound internet access.
5. Set a sufficiently long timeout for non-streaming multimodal requests.
6. Start with enough memory for Streamlit, then tune using observed metrics.

After deployment:

```bash
curl -i https://<function-public-url>/_stcore/health
```

Repeat Freeform, one image case, and one video case through the public UI.

## 9. Evidence record

Keep actual results outside the source documentation, for example in CI logs,
a release record, or hackathon evidence:

| Check | Result | Evidence |
|---|---|---|
| unit tests | pass/fail | terminal or CI log |
| text/image/video smoke tests | pass/fail | terminal log |
| local Streamlit | pass/fail | screenshot |
| FC health | pass/fail | curl output |
| FC UI | pass/fail | URL and screenshot/video |
| ZIP size | value | `du -h code.zip` |
| cold start / response time | value | FC and browser logs |
