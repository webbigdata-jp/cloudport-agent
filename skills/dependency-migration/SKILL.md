---
name: dependency-migration
description: Rewrite Python dependencies and build environments when porting Gemini applications to Qwen/Alibaba Cloud. Use when editing pyproject.toml, requirements.txt, uv.lock, deployment ZIP dependencies, Python runtime versions, native wheels, or replacing google-genai with openai.
---

# Dependency Migration: Gemini → Qwen

Keep runtime dependencies, development tooling, and deployment-build tooling
separate. A correct import list is not sufficient if the deployment artifact
contains wheels for the wrong OS, architecture, or Python ABI.

## Decision table

| Package/tool | Action | Condition |
|---|---|---|
| `google-genai` | remove | only after all intended Gemini call sites are ported |
| `openai` | add | for Model Studio OpenAI-compatible API |
| `google-api-python-client` | keep | when used by unrelated Google Data APIs |
| `pydantic` | keep | reuse schemas for local validation |
| datastore/scientific packages | keep | unless independently changed |
| `pip` | build tool, not normally app dependency | do not `uv add pip` merely to build an FC ZIP |

## Procedure

1. Read the project profile and identify the dependency source of truth:
   `pyproject.toml`/lockfile, one or more requirements files, or a deployment
   manifest.
2. Grep before removal:
   `grep -rn "google.genai\|from google import genai" --include='*.py' .`
3. Inventory related but non-Gemini Google packages. Do not remove by prefix.
4. Verify the current OpenAI SDK release and `Requires-Python` in official/PyPI
   metadata before setting a bound. Do not pin from memory.
5. Update the canonical dependency file, then regenerate generated locks with
   the project's tool. Never hand-edit `uv.lock`.
6. Update environment examples and operational docs across the repository.
7. Recreate a clean environment and resolve/install from scratch.
8. If building a ZIP/container/layer, validate the target runtime separately
   from the local developer environment.

## Deployment artifact dependencies

For a self-contained Python ZIP, determine:

- target OS and architecture;
- target Python major/minor version and ABI;
- whether dependencies include native wheels (`pyarrow`, `numpy`, etc.);
- maximum package/upload size;
- whether build and runtime filesystems are writable.

Do not claim that a native macOS/Windows installation is a Linux FC package.
Build on a compatible Linux host/WSL/container, or use an explicitly verified
cross-platform wheel-download workflow.

For a profile that targets Linux x86_64 and Python `${PYTHON_VERSION}`, a robust
pattern is:

```bash
uv venv .venv-fc --python "$PYTHON_VERSION" --seed
PYTHON_BIN=.venv-fc/bin/python
"$PYTHON_BIN" -m pip install \
  --disable-pip-version-check \
  --only-binary=:all: \
  --target .fc-build \
  --requirement requirements.txt
```

Why:

- the deployment build does not depend on `/usr/bin/python3 -m pip`;
- the project `.venv` can use a different Python without contaminating the
  artifact;
- `pip` remains in an ephemeral build environment, not application metadata;
- the installer and target Python minor version are explicit.

`uv pip install --target` can also build a target directory, but do not mix
its interpreter selection implicitly with a different project `.venv`. Whichever
installer is chosen, print and validate the selected Python version and target
platform in the build log.

Read [fc-zip-dependencies.md](fc-zip-dependencies.md) for the complete packaging
checklist.

## Multiple dependency groups

Some repositories have separate local pipeline and cloud runtime dependencies.
Document which file/group serves each component. Do not merge them merely for
convenience; serverless packages should not inherit unrelated development or
batch dependencies.

For a small standalone example, prefer one runtime source of truth and keep
build/test commands outside it.

## Staged migration

If both providers coexist temporarily:

- keep both SDKs only while both paths are reachable;
- gate selection explicitly with configuration;
- test both paths;
- remove the old SDK in a dedicated cleanup after the final call site is gone.

Never silently delete an optional Gemini feature because its key is absent.
