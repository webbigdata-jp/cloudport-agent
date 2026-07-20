# FC ZIP dependency checklist

Use this reference when a Python application is deployed as a self-contained
Function Compute ZIP.

## Select the target before building

Resolve and record:

- FC region;
- built-in/custom runtime mode;
- currently supported Python runtime identifier;
- OS/architecture;
- compressed package-size limit for the chosen upload method.

Do not infer the FC Python version from a source Dockerfile. At the 2026-06-02
FC documentation revision, Python 3.12 public preview was the newest listed
built-in Python runtime and Python 3.13 was not listed. Re-check the official
page for every build:
https://www.alibabacloud.com/help/en/functioncompute/fc/python/

## Build-host checks

```bash
uname -s
uname -m
"$PYTHON_BIN" -c 'import sys; print(sys.version); print(sys.implementation.cache_tag)'
```

Compare these with the configured FC runtime. Native wheels must match the
runtime platform and Python ABI.

## Isolation

Use a deployment-specific environment such as `.venv-fc`; do not rely on:

- a currently activated project environment;
- `/usr/bin/python3` having pip;
- `pip` resolving to the intended Python;
- package installation during function startup.

Invoke pip through the intended interpreter:

```bash
"$PYTHON_BIN" -m pip ...
```

## Target-directory installation

Install into the archive package root, not inside the build venv:

```bash
"$PYTHON_BIN" -m pip install \
  --only-binary=:all: \
  --target "$BUILD_DIR" \
  --requirement requirements.txt
```

Create the ZIP from inside `BUILD_DIR` so imports and entrypoints are at archive
root.

## Cross-target installation

For CPython `${PYTHON_VERSION}` on Linux x86_64, make the target explicit. Do
not rely on the host venv alone:

```bash
"$PYTHON_BIN" -m pip install \
  --only-binary=:all: \
  --platform manylinux2014_x86_64 \
  --python-version "$PYTHON_VERSION" \
  --implementation cp \
  --abi "$PYTHON_ABI" \
  --target "$BUILD_DIR" \
  --requirement requirements.txt
```

On Apple Silicon, Docker commands for an x86_64 target must include:

```bash
docker run --rm --platform linux/amd64 ...
```

Without that flag, Docker can correctly build the wrong Linux architecture.

## Validation

- import/compile tests pass in the developer environment;
- the exact generated build script runs end-to-end with exit status 0;
- archive contains the application entrypoint and imported packages;
- archive excludes docs, tests, secrets, local venvs, and build scripts unless
  required at runtime;
- runtime Python minor version equals the verified FC target;
- every native extension is inventoried, not just one representative file;
- native extension imports are exercised in an unpacked-package test inside a
  target-compatible Linux/architecture/Python environment;
- no startup path executes `pip`, `uv`, `npm`, or `npx -y` downloads;
- compressed size is checked against the target region and upload path.

Native-extension inventory example:

```bash
find "$BUILD_DIR" -type f \
  \( -name '*.so' -o -name '*.pyd' -o -name '*.dylib' \) \
  -print0 | xargs -0 file
```

A successful `file` result such as "ELF 64-bit x86-64" proves only binary
format/architecture. It does not prove imports, shared-library compatibility, or
application startup. If no target-compatible runtime is available, report:

- native binary format: PASS;
- unpacked package imports: NOT RUN;
- bootstrap/health: NOT RUN.

## Common diagnosis

| Symptom | Likely cause |
|---|---|
| `/usr/bin/python3: No module named pip` | build script invoked system Python instead of the seeded build venv |
| package installs but ZIP fails on FC | OS/architecture/Python ABI mismatch |
| `python` not found in bootstrap | runtime exposes `python3`/versioned executable only |
| artifact is unexpectedly huge | development packages, duplicate environments, or heavy transitive native packages were included |
| Docker build works but FC fails | Docker built linux/arm64 on Apple Silicon instead of linux/amd64 |
| ELF inspection passes but import fails | binary-format check was mistaken for target-runtime compatibility |
| build log stops after ZIP creation | `pipefail` plus an early-closing `head`/`grep -q` pipeline |
| cold start times out | runtime dependency download or oversized initialization |

Golden implementation:
`examples/gemini-streamlit-cloudrun-to-qwen-fc/deploy.sh`.
