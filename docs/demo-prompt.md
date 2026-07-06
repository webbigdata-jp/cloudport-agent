# CloudPort Agent demo prompt

```text
You are Qwen Code working inside a repository that currently contains a Gemini/GCP-based AI application.

Use the CloudPort Agent skills to prepare a Gemini-to-Qwen Cloud migration.

Goals:
1. Scan the repository and identify Gemini API call sites, embedding generation, structured-output usage, dependency files, environment variables, ADK agent structure, and deployment assumptions.
2. Produce a migration plan first. Do not edit files until the plan is approved.
3. Convert Gemini LLM calls to Qwen/DashScope-compatible calls using the OpenAI-compatible API where appropriate.
4. Convert Gemini embedding usage to Qwen text-embedding usage while preserving vector-index compatibility. Do not mix embedding vector spaces.
5. Replace Gemini response_schema behavior with JSON-mode prompting plus local Pydantic validation when needed.
6. Update dependency files carefully. If this project uses multiple requirements files or dependency groups, explain which one is used for local pipeline scripts and which one is used for cloud deployment.
7. Validate the migration with schema checks, smoke-run instructions, and a list of files changed.
8. Provide Alibaba Cloud Function Compute deployment advice, but do not perform billing-scoped or credential-scoped cloud actions yourself.

Important constraints:
- Human approval is required before the migration plan, before each file diff is applied, and before deployment.
- Do not remove unrelated Google imports or packages unless they are clearly part of the Gemini migration.
- Do not introduce runtime package downloads in Function Compute. Deployment artifacts must be self-contained.
- If the repository already uses MongoDB Atlas Vector Search, verify embedding dimensions before recommending any re-indexing.
- Prefer minimal diffs over broad rewrites.

Please start by scanning the repository and presenting the migration plan.
```
