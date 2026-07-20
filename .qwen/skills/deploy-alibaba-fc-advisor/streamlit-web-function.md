# Streamlit on Function Compute: Web Function Custom Runtime ZIP

Use this reference only when the project profile chooses this deployment
method. It is not a universal FC recipe.

## Runtime capability gate

Do not copy the Python version from the source Dockerfile into the FC ZIP
configuration. Resolve the target in this order:

1. identify the target FC region and deployment type;
2. read the current official FC Python runtime table;
3. confirm the runtime identifier and executable available in that region;
4. choose the build Python/ABI to match it;
5. if the required source version is unsupported, retarget, bundle the runtime,
   or use a Custom Container.

At the time of the clean-room regression (official page updated 2026-06-02),
FC listed Python 3.12 public preview as the newest built-in Python runtime and
did not list Python 3.13. Treat this as a dated observation, not a permanent
hardcode; always re-check:
https://www.alibabacloud.com/help/en/functioncompute/fc/python/

A Web Function with Custom Runtime permits an arbitrary HTTP framework. It does
not mean that `python3.13` or any other arbitrary interpreter is preinstalled.
Do not emit instructions such as "select Custom Runtime (Python 3.13)" unless
the target console and runtime have been verified.

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

### Cross-platform build requirements

For an x86_64 FC target from Apple Silicon/macOS:

- Docker builds must specify `--platform linux/amd64`; otherwise Docker may
  silently produce Linux arm64 dependencies.
- Cross-target pip installs must explicitly set the target Python version,
  implementation, ABI, and platform; do not rely only on the host venv version.
- Never claim dependencies are pure Python without inspecting the resolved
  artifact. Streamlit commonly brings native packages such as `pyarrow`,
  `numpy`, `pydantic-core`, or Pillow.

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
preserves it. Keep the manifest file until all reporting is complete. Under
`pipefail`, `unzip -Z1 code.zip | head -20` has the same early-consumer/SIGPIPE
risk; print with `sed -n '1,20p' "$manifest"` instead.

The generated build script itself is a deliverable. Execute that exact script
end-to-end with tracing/log capture and require:

- exit status 0;
- the expected final success marker;
- the expected archive hash/size; and
- no silent stop after ZIP creation.

Manually running equivalent commands does not validate the script.

## Startup and health must be separable from provider credentials

Prefer lazy Model Studio client initialization so Streamlit and
`/_stcore/health` can start without a valid API key. Missing credentials should
produce a controlled UI state when a generation action is attempted, not a raw
process crash. If the application deliberately requires credentials at startup,
document that design and run the health test with a dummy value that triggers no
provider request.

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

Run this in a target-compatible Linux x86_64 environment. A macOS failure to
import an ELF extension is expected and does not prove the package works. If a
Linux runtime is unavailable, report the import/startup check as NOT RUN and
record only the narrower binary-format evidence.

## Web Function startup semantics

For this pattern, startup is controlled by the root `bootstrap` or the configured
startup command. Do not invent an event-function handler such as `index.handler`
unless the chosen FC screen/API explicitly requires it and the project profile
documents why.

## Human deployment checklist additions

- select a currently supported runtime, then build the package for that exact
  Python minor version and architecture;
- compare the ZIP size with the target region/upload-method quota;
- upload only the generated ZIP;
- configure `DASHSCOPE_API_KEY` and an endpoint from the same workspace/region;
- allow outbound network access required by Model Studio and remote media;
- set memory/timeout appropriate for Streamlit and multimodal inference;
- verify `/_stcore/health`, then the public UI;
- compare cold and warm request latency;
- retain the prior ZIP/version for rollback.

Official references to re-check:

- FC Python runtimes and regional availability:
  https://www.alibabacloud.com/help/en/functioncompute/fc/python/
- FC environment variables:
  https://www.alibabacloud.com/help/en/functioncompute/fc/user-guide/environment-variables
- FC quotas/package-size limits:
  https://www.alibabacloud.com/help/en/functioncompute/limits-of-usage
- Golden build/bootstrap:
  `examples/gemini-streamlit-cloudrun-to-qwen-fc/deploy.sh`
