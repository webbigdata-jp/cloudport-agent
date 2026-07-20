# Gemini Streamlit → Qwen Model Studio / Alibaba Cloud Function Compute

This directory is a runnable CloudPort Agent migration example. It keeps the
original Streamlit application structure close to the Gemini sample while
isolating Qwen/Model Studio request differences in `cloudport_compat.py`.

## Repository structure

```text
.
├── app.py                       # Streamlit application
├── cloudport_compat.py          # Gemini-style compatibility layer for Qwen
├── requirements.txt             # Runtime dependencies; single source of truth
├── deploy.sh                    # Builds the FC upload ZIP
├── smoke_test.py                # Live text/image/video API checks
├── tests/
│   └── test_cloudport_compat.py # Offline payload and endpoint unit tests
├── docs/
│   ├── MIGRATION.md             # Provider and deployment mapping notes
│   ├── TESTING.md               # Local, ZIP, and FC verification procedure
│   └── REPO_INTEGRATION.md      # Integration plan for cloudport-agent
└── .gitignore
```

## What `deploy.sh` uploads

`deploy.sh` creates `code.zip` containing only:

- `app.py`
- `cloudport_compat.py`
- generated executable `bootstrap`
- installed runtime dependencies
- optional `.streamlit/config.toml`, when present

It does **not** package `main.py`, `pyproject.toml`, README/docs, tests,
`smoke_test.py`, `requirements.txt`, or `deploy.sh` itself.

## Prerequisites

The ZIP builder must run on **Linux x86_64** because it installs host-native
Python wheels. WSL2 on an x86_64 Windows machine is supported. Native macOS and
native Windows builds are intentionally rejected.

Required commands:

```bash
uv zip unzip
```

The Function Compute custom runtime must provide Python 3.12.

## Quick verification

```bash
python3 -m compileall -q app.py cloudport_compat.py smoke_test.py tests
python3 -m unittest discover -s tests -v
bash -n deploy.sh
```

For live API tests:

```bash
export DASHSCOPE_API_KEY='...'
export DASHSCOPE_BASE_URL='https://<workspace-id>.<region>.maas.aliyuncs.com/compatible-mode/v1'
python3 smoke_test.py --mode all
streamlit run app.py
```

## Validate and build the Function Compute ZIP

Validate the host and source manifest without downloading Python or packages:

```bash
CHECK_ONLY=1 ./deploy.sh
```

Build the upload artifact:

```bash
./deploy.sh
unzip -l code.zip | head -50
```

The builder removes `.fc-build/` and `.venv-fc/` after success, leaving only
`code.zip`. Set `KEEP_BUILD_DIR=1` when the unpacked build directory is needed
for debugging.

See [docs/TESTING.md](docs/TESTING.md) for the complete procedure and
[docs/MIGRATION.md](docs/MIGRATION.md) for the migration rationale.
