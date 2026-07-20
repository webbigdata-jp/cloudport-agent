# FC ZIP dependency checklist

Use this reference when a Python application is deployed as a self-contained
Function Compute ZIP.

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

## Validation

- import/compile tests pass in the developer environment;
- archive contains the application entrypoint and imported packages;
- archive excludes docs, tests, secrets, local venvs, and build scripts unless
  required at runtime;
- runtime Python minor version equals the build target;
- native extension imports are exercised in an unpacked-package test;
- no startup path executes `pip`, `uv`, `npm`, or `npx -y` downloads.

## Common diagnosis

| Symptom | Likely cause |
|---|---|
| `/usr/bin/python3: No module named pip` | build script invoked system Python instead of the seeded build venv |
| package installs but ZIP fails on FC | OS/architecture/Python ABI mismatch |
| `python` not found in bootstrap | runtime exposes `python3`/versioned executable only |
| artifact is unexpectedly huge | development packages or duplicate environments were included |
| cold start times out | runtime dependency download or oversized initialization |

Golden implementation:
`examples/gemini-streamlit-cloudrun-to-qwen-fc/deploy.sh`.
