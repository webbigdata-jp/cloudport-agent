---
name: project-profile-generator
description: Scan an unfamiliar repository and draft a Migration Project Profile for a Gemini-to-Qwen port. Use whenever the user points CloudPort Agent at a NEW project, repo, or codebase that has no project-* skill yet, or asks "can you migrate this project" / "analyze this repo for migration". This is always the FIRST step for an unknown project.
---

# Project Profile Generator

Turns an unknown repository into a reviewable migration plan. The
output is a DRAFT that a human approves or edits — never start editing
code from an unapproved profile.

## Scan procedure

1. Inventory LLM call sites:
   - `grep -rn "google.genai\|from google import genai" --include='*.py'`
   - Classify each hit: `generate_content` / `embed_content` /
     structured output (`response_schema`) / other.
2. Inventory non-targets (report them, do not port them):
   - `google-api-python-client` usage (YouTube etc.) — unrelated.
   - Files where Gemini is optional (guarded by env-var checks).
3. Locate configuration:
   - `.env` files and where they are loaded from (watch for hardcoded
     relative paths — a known source-project bug class).
   - `pyproject.toml` / `requirements.txt` / lockfiles.
4. Identify data stores and vector indexes (search for `pymongo`,
   `numDimensions`, vector index definitions) — flag any re-embed
   backfill requirement.
5. Identify the execution entry points and their order (shell scripts,
   cron, CI).

## Output: the profile draft

Write the result as a NEW project skill at
`.qwen/skills/project-<name>/SKILL.md`, using
`project-soccerscope` in this repo as the reference template. Keep it
under ~60 lines: target files, non-targets, env vars, datastore notes,
execution order, open questions.

Include a `paths:` frontmatter gate scoped to the project's directory
so the profile only activates when relevant files are touched.

## Human-in-the-loop

Present the draft with: files to be modified (exact list), files
explicitly out of scope, and open questions. Proceed to
`gemini-to-qwen-api-mapping` only after explicit approval.

This one-file-per-project design is what makes CloudPort general:
the core skills never change; each new project adds one thin profile.
