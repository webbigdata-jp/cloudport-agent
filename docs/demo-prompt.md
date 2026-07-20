# CloudPort Agent demo prompt

Recommended Qwen Code mode for a long autonomous run with safety guardrails:

```text
/approval-mode auto
```

Then use:

```text
You are Qwen Code working inside a repository that contains a Gemini / Google Cloud AI application.

Use the CloudPort Agent skills to complete a supervised Gemini-to-Qwen Cloud migration.

Goals:
1. Scan the repository across source code, dependency manifests, configuration, infrastructure, CI, and deployment scripts. Identify Gemini SDK, Vertex AI, JavaScript / TypeScript SDKs, REST endpoints, LiteLLM or provider configuration, embeddings, multimodal calls, structured output, environment variables, ADK structure, and deployment assumptions.
2. Create a migration plan as a reviewable artifact, then continue the repository migration automatically. Do not wait for separate plan or per-diff approval.
3. Convert Gemini calls to Qwen / DashScope-compatible calls, using the OpenAI-compatible API where appropriate.
4. Convert embedding usage while preserving dimensions and vector-index compatibility. Never mix embedding vector spaces.
5. Replace provider-specific structured-output behavior with prompt schema instructions, local validation, and retries where needed.
6. Update canonical dependency files and regenerate generated lockfiles with the repository's package manager. Preserve unrelated Google packages and integrations.
7. Run offline tests, syntax checks, package validation, and project-specific smoke checks. Diagnose and repair failures until checks pass or a concrete external blocker is identified.
8. Build and validate a self-contained Alibaba Cloud Function Compute artifact and provide exact deployment instructions.

Safety boundary:
- Use Qwen Code approval and permission controls for commands classified as risky or destructive.
- Routine repository analysis, edits, builds, tests, and repairs should proceed automatically in the selected safe approval mode.
- Do not create cloud resources, use production credentials, rebuild billable indexes, or deploy to production. Prepare the artifacts and exact commands, and leave these spend- or availability-changing operations to the human operator.
- Do not introduce runtime package downloads in Function Compute. Deployment artifacts must be self-contained.
- Prefer minimal, reviewable diffs over broad rewrites.

Deliverables:
- generated project profile;
- migration plan;
- changed-file list and diffs;
- tests executed and their exact results;
- repaired failures and remaining external blockers;
- validated Function Compute artifact summary;
- exact human-run cloud deployment commands.

Start by scanning the repository, then complete the repository migration and validation workflow.
```
