---
name: project-profile-generator
description: Scan an unfamiliar repository and create a Migration Project Profile for a Gemini-to-Qwen port. Use whenever CloudPort Agent is pointed at a new project, repository, or codebase without a project-* profile. This is the first migration step for an unknown project and should continue automatically into mapping, editing, and validation unless a concrete high-impact ambiguity blocks safe progress.
---

# Project Profile Generator

Turn an unknown repository into a thin, reviewable migration profile, then route the result into the core migration skills. The profile is an audit artifact, not a mandatory human approval gate.

## Scan procedure

### 1. Search every relevant provider surface

Prefer `rg` and exclude generated/vendor directories:

```bash
rg -n --hidden \
  --glob '!.git/**' \
  --glob '!node_modules/**' \
  --glob '!vendor/**' \
  --glob '!dist/**' \
  --glob '!build/**' \
  -e 'google\.genai' \
  -e 'from google import genai' \
  -e 'google\.generativeai' \
  -e 'vertexai' \
  -e 'google\.cloud\.aiplatform' \
  -e '@google/genai' \
  -e '@google/generative-ai' \
  -e 'generativelanguage\.googleapis\.com' \
  -e 'aiplatform\.googleapis\.com' \
  -e 'gemini[-_/][A-Za-z0-9._-]+' \
  -e 'provider[^\n]*(gemini|vertex)' \
  .
```

If `rg` is unavailable, use `grep -RInE` with equivalent exclusions. Do not limit discovery to `*.py`.

Classify every hit as one or more of:

- text generation or chat;
- image / audio / video input;
- embeddings and retrieval task types;
- structured output / JSON schema;
- tool or function calling;
- thinking / reasoning controls;
- model routing through LiteLLM, LangChain, ADK, environment variables, YAML, JSON, or Terraform;
- direct REST request.

### 2. Inventory non-target Google usage

Report and preserve unrelated integrations such as YouTube, Google Drive, Google Sheets, Firebase, authentication, storage, analytics, and other `google-cloud-*` packages. Do not remove packages merely because their names begin with `google`.

### 3. Locate dependency and configuration sources of truth

Inspect:

- `pyproject.toml`, `requirements*.txt`, `uv.lock`, Poetry / Pipenv files;
- `package.json`, npm / pnpm / Yarn lockfiles;
- `.env.example`, settings modules, YAML / JSON / TOML configuration;
- Dockerfiles, Compose, shell scripts, CI workflows, Terraform, Kubernetes, Serverless, and cloud manifests.

Record API-key names, endpoints, regions, runtime versions, OS / architecture assumptions, and generated lockfiles. Never copy secret values into the profile.

### 4. Identify data and execution constraints

- Find vector indexes, embedding dimensions, backfill jobs, and mixed-vector-space risks.
- Identify entry points, scheduled jobs, queues, web handlers, and execution order.
- Identify existing tests, smoke checks, deployment packaging, health checks, and production-only dependencies.
- Separate checks that can run offline from checks requiring credentials, billable services, or production access.

## Output

Write the canonical profile to `skills/project-<name>/SKILL.md` and mirror it to `.qwen/skills/project-<name>/SKILL.md`. Use `project-soccerscope` as the structural reference.

Keep the profile thin and operational. Include:

- exact target files and call-site classes;
- files and integrations explicitly out of scope;
- dependency sources of truth;
- environment variable names and region assumptions;
- embedding / datastore constraints;
- execution and test commands;
- deployment-package constraints;
- unresolved questions and their risk level.

Add a `paths:` frontmatter gate scoped to the project where supported.

## Autonomy and blocking rules

After writing the profile, continue automatically to `gemini-to-qwen-api-mapping`, `dependency-migration`, `migration-validation`, and deployment-artifact preparation.

Do not stop merely to request approval for the profile, migration plan, or each diff. Stop only when:

- Qwen Code's permission system blocks or requests a decision for a risky operation;
- a destructive action is genuinely necessary and has no safe alternative;
- credentials, billable cloud resources, or production deployment are required;
- an unresolved ambiguity could cause data loss, security exposure, material spend, or an incompatible vector-index rebuild.

When blocked, report the exact decision needed and continue all independent safe work first.
