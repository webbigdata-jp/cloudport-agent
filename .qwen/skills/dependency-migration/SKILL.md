---
name: dependency-migration
description: Rewrite Python project dependencies when porting from the Gemini stack to Qwen Cloud. Use whenever editing pyproject.toml, requirements.txt, or uv.lock as part of a Gemini-to-Qwen migration, or when the user asks to "clean up dependencies", "remove google-genai", or "add the Qwen SDK".
---

# Dependency Migration (Gemini stack → Qwen Cloud)

## Decision table

| Package | Action | Why |
|---|---|---|
| `google-genai` | REMOVE (only after all call sites are ported) | Gemini SDK |
| `openai` | ADD (pin `>=` current major; check docs) | Qwen Cloud is OpenAI-compatible |
| `google-api-python-client` | KEEP if the project calls YouTube/other Google Data APIs | Unrelated to Gemini |
| `pydantic` | KEEP, same version | Schemas are reused for validation |
| `pymongo`, `numpy`, `python-dotenv` | KEEP | Not LLM-related |

## Procedure

1. The dependency file format used by the project (pyproject/uv or requirements.txt) may be defined in the project profile. Please check there before looking for the file.

2. Grep first, edit second:
   `grep -rn "google.genai\|from google import genai" --include='*.py'`
   Do not remove `google-genai` from pyproject.toml while any hit remains.
3. Before pinning the `openai` package version, check PyPI / official
   docs for the current release and its `Requires-Python`. Do not pin
   from memory.
4. Edit `pyproject.toml`, then regenerate the lockfile
   (`uv lock` for uv projects). Never hand-edit `uv.lock`.
5. Update `.env.example` / README: `GEMINI_API_KEY` → `DASHSCOPE_API_KEY`.
   Search docs and shell scripts for the old env var name too:
   `grep -rn "GEMINI_API_KEY"` across the whole repo, not just `*.py`.
6. Commit the dependency change as its own commit, separate from code
   changes ("move files → commit each step" — a lesson learned the
   hard way in the source project).

## Gotchas

- Some projects use Gemini OPTIONALLY (feature auto-skips when the key
  is unset). Decide per-file: port it, or leave it Gemini-optional and
  document that. Do not silently delete optional features.
- If both stacks must coexist during a staged rollout, keep both SDKs
  temporarily and gate by env var; remove `google-genai` in a final
  cleanup commit.
