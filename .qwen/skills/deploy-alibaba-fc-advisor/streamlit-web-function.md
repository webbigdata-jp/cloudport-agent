# Streamlit on Function Compute: Web Function Custom Runtime ZIP

Use this reference only when the project profile chooses this deployment
method. It is not a universal FC recipe.

## Build artifact

The ZIP should normally contain at archive root:

- application entrypoint;
- imported application modules;
- vendored runtime dependencies;
- executable `bootstrap` if the FC configuration relies on it;
- optional `.streamlit/config.toml` required at runtime.

Exclude docs, tests, local environments, secrets, smoke-test tooling, and build
scripts unless the application imports them at runtime.

Build dependencies with the target Python version on a compatible platform.
See `dependency-migration/fc-zip-dependencies.md`.

## Bootstrap properties

A robust generated bootstrap:

1. resolves and `cd`s to its own directory;
2. sets `HOME` or other writable caches to `/tmp`;
3. resolves the runtime Python without assuming `python` exists;
4. verifies that runtime Python major/minor matches the build target;
5. replaces the shell process with Streamlit;
6. binds to all interfaces and FC's injected port;
7. disables Streamlit development mode when target-directory packaging causes
   source-tree detection.

Template, parameterized by the project target version:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export HOME="${STREAMLIT_HOME:-/tmp}"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if [[ -n "${PYTHON_BIN:-}" ]]; then
  runtime_python="$PYTHON_BIN"
elif command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then
  runtime_python="$(command -v "python${PYTHON_VERSION}")"
elif command -v python3 >/dev/null 2>&1; then
  runtime_python="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  runtime_python="$(command -v python)"
else
  echo "ERROR: compatible Python runtime not found" >&2
  exit 127
fi

runtime_version="$($runtime_python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$runtime_version" != "$PYTHON_VERSION" ]]; then
  echo "ERROR: package targets Python $PYTHON_VERSION; runtime is $runtime_version" >&2
  exit 1
fi

exec "$runtime_python" -m streamlit run app.py \
  --global.developmentMode=false \
  --server.address=0.0.0.0 \
  --server.port="${FC_CUSTOM_LISTEN_PORT:-9000}" \
  --server.headless=true
```

When generating this file from a build script, substitute or export
`PYTHON_VERSION` deliberately; do not leave an unset variable in the deployed
bootstrap.

## Why development mode may need an override

With `pip install --target <archive-root>`, the `streamlit/` package is not
located under a conventional `site-packages` path. Streamlit can classify that
layout as a development/source checkout. Development mode conflicts with an
explicit server port, so the validated pattern sets
`--global.developmentMode=false`.

## Package manifest validation

Under `set -euo pipefail`, avoid this form:

```bash
unzip -l code.zip | grep -q app.py
```

`grep -q` may exit after the match and cause the producer to receive SIGPIPE,
which `pipefail` treats as failure. Instead:

```bash
manifest="$(mktemp)"
unzip -Z1 code.zip > "$manifest"
grep -Fx app.py "$manifest" >/dev/null
grep -Fx bootstrap "$manifest" >/dev/null
```

Also check forbidden root entries and executable mode where the archive/runtime
preserves it.

## FC-equivalent local test

```bash
rm -rf /tmp/app-fc-test
mkdir -p /tmp/app-fc-test
unzip -q code.zip -d /tmp/app-fc-test
cd /tmp/app-fc-test
export FC_CUSTOM_LISTEN_PORT=9000
./bootstrap
```

From another shell:

```bash
curl -fsS http://127.0.0.1:9000/_stcore/health
```

Expected response: `ok`.

## Human deployment checklist additions

- select the runtime matching the package Python minor version;
- upload only the generated ZIP;
- configure `DASHSCOPE_API_KEY` and an endpoint from the same workspace/region;
- allow outbound network access required by Model Studio and remote media;
- set memory/timeout appropriate for Streamlit and multimodal inference;
- verify `/_stcore/health`, then the public UI;
- compare cold and warm request latency;
- retain the prior ZIP/version for rollback.

Official references to re-check:

- FC environment variables:
  https://www.alibabacloud.com/help/en/functioncompute/fc/user-guide/environment-variables
- Golden build/bootstrap:
  `examples/gemini-streamlit-cloudrun-to-qwen-fc/deploy.sh`
