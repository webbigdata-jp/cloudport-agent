# CloudPort Agent

**Gemini-to-Qwen Cloud migration copilot, packaged as native Qwen Code Agent Skills.**

![Demo time](https://img.shields.io/badge/demo_time-about_5_min-orange)
![Human approvals](https://img.shields.io/badge/human_approvals-8-blue)
![Files changed](https://img.shields.io/badge/files_changed-2-green)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

CloudPort Agent helps migrate production Gemini / Google Cloud applications to Qwen on Alibaba Cloud by turning real migration experience into reusable, model-invoked Qwen Code Agent Skills.

---

# Why

Production AI apps are quietly locked in. Working Gemini, Vertex,Google Cloud, OpenAI, or AWS assumptions are baked into code, config,
dependencies, deployment scripts — and vector indexes. Migration costIS vendor lock-in. CloudPort Agent attacks that cost directly: it makes
your AI stack portable, so you can stand up a backup site on a second cloud, keep pricing leverage, and remove single-provider risk.

### Why Gemini → Qwen / Alibaba Cloud first

The porting pattern is general, but our shipped skills cover the migration with the clearest payoff today:

- **Cost — at agent-scale context, where it actually matters.**
  Flagship vs flagship (per 1M tokens, as of this writing):
  Qwen3.7-Max runs $2.50 in / $7.50 out at a single flat rate
  ($1.25 / $3.75 under the promotional pricing through Jul 23, 2026),
  while Gemini 3.1 Pro charges $2.00 / $12.00 — jumping to
  $4.00 / $18.00 once a prompt exceeds 200K tokens. Here's the
  catch: in the agent era, sub-200K prompts barely exist. A single
  ~5-minute CloudPort Agent run migrating just two scripts consumed
  ~80% of a 1M-token allowance. Repo-aware agents live above the
  200K threshold, so Gemini's long-context tier is the *realistic*
  rate — making Qwen roughly **55% cheaper for agent workloads**
  (~77% under the current promotion), with no surcharge cliff to
  engineer around.
  
- **An open-weights escape hatch.** Qwen models are open. Teams
  already self-hosting Qwen on their own GPUs can scale out to
  Alibaba Cloud without changing model family. There is no
  self-host path back out of Gemini.
- **Business continuity, proven.** We run the same production app on
  both clouds today: SoccerScope on Gemini/Cloud Run and its migrated
  twin on Qwen/Alibaba Cloud Function Compute. Same app, two clouds,
  migrated by an agent with human-in-the-loop approval gates.

Alibaba Cloud holds only ~4% of the global cloud market despite competitive models, 
because migration cost blocks the door. These Agent Skills are that door's key, 
in both directions of the argument: easier to come in, and never locked in.

---

## What it does

Point Qwen Code at a Gemini-based repository and CloudPort Agent follows a human-approved migration loop:

1. **Scan** the repository and identify Gemini call sites, Google imports that are not migration targets, environment variables, dependency files, embedding usage, ADK agent structure, and deployment assumptions.
2. **Plan** the migration before touching files, including API mapping, dependency changes, validation checks, and deploy impact.
3. **Patch** LLM call sites from Gemini SDK patterns to DashScope / Qwen-compatible patterns, including JSON output and local schema validation where needed.
4. **Validate** schema-level equivalence, embedding-dimension compatibility, smoke-run behavior, and "do not mix vector spaces" constraints.
5. **Advise deployment** on Alibaba Cloud Function Compute, with exact human-executed steps rather than blind autonomous cloud changes.

Human-in-the-loop is a design principle. The plan, file diffs, and deployment actions pass through approval gates. Billing-scoped and authentication-scoped cloud actions are advisory by design: the agent writes the checklist, and the human runs it.

The reference migration target uses an ADK-based agent layer (`google.adk.agents`). That matters for portability: the CloudPort Skills are written around migration patterns, validation rules, and deployment constraints, so they should be relatively easy to adapt to other model backends that also use ADK-style agent structure.

---

## What the Migration Actually Touches

CloudPort Agent is not a find-and-replace for API keys.
The Gemini→Qwen migration spans four layers:

### 1. LLM swap via Custom Skills
Google ADK agent core rewired from Gemini to Qwen
(`dashscope/qwen-plus` via LiteLLM) — framework untouched.

### 2. RAG re-indexing with Qwen Embeddings
The app runs RAG over MongoDB Atlas Vector Search.
Embeddings migrated from Gemini to Qwen `text-embedding-v4`
(DashScope OpenAI-compatible API). Vectors from different
models are not interchangeable, so the corpus is re-embedded
and the vector search index regenerated.

### 3. MCP server integration on serverless
The app uses the official MongoDB MCP server. On Cloud Run it
ran via `npx`; Function Compute 3.0 Custom Runtime has no
Node on PATH, so the invocation was rewritten to a direct
`node` call with `node_modules` bundled at build time.

### 4. Structured output compatibility layer
Gemini's `response_schema=` has no DashScope equivalent.
Replaced with schema-in-prompt + local Pydantic validation
+ retry-on-mismatch.

---

## Architecture

CloudPort Agent is best understood as three diagrams: the migration overview, the reusable skill system, and the post-migration runtime layout.

### 1. Migration overview

![Migration overview](docs/architecture_1_migration_overview.png)

CloudPort Agent sits between a **GCP with Gemini** source stack and a **Qwen with Alibaba Cloud** target stack. The migration copilot runs inside Qwen Code, uses CloudPort Skills, and keeps plan / diff / deploy actions behind human approval gates.

### 2. Skills architecture

![Skills architecture](docs/architecture_2_skills_architecture.png)

The skills are split into reusable core migration skills, a generalizer that drafts thin project profiles, and project-specific profiles such as `project-soccerscope`.

### 3. What runs where after migration

![Runtime layout](docs/architecture_3_runtime_layout.png)

The migrated SoccerScope example uses local pipeline scripts, Alibaba Cloud Function Compute, Qwen Cloud / DashScope, and MongoDB Atlas Vector Search. The agent's brain also runs on Alibaba Cloud via Qwen Code / Qwen Cloud.

See also: [`docs/SKILLS_ARCHITECTURE.md`](docs/SKILLS_ARCHITECTURE.md)

---

## Skills catalog

| Skill | Role | One-line description |
|---|---|---|
| `gemini-to-qwen-api-mapping` | Core | Maps Gemini SDK usage to Qwen / DashScope-compatible API patterns, including JSON output and local validation. |
| `dependency-migration` | Core | Updates dependency files, lockfiles, import expectations, and environment variable layout without touching unrelated Google packages. |
| `migration-validation` | Core | Defines equivalence checks, schema checks, vector-index compatibility checks, and smoke-run sign-off gates. |
| `deploy-alibaba-fc-advisor` | Core | Produces Alibaba Cloud Function Compute deployment advice and human-executed checklists. |
| `project-profile-generator` | Generalizer | Scans an unfamiliar repository and drafts a thin project profile for human approval. |
| `project-soccerscope` | Project profile | Reference profile encoding SoccerScope-specific paths, ADK structure, constraints, and migration lessons. |

---

## Quickstart

CloudPort Agent is distributed as Qwen Code Agent Skills. There is no framework server to run.

### Option 1: Install as project skills

Copy the skills into the target repository:

```bash
mkdir -p /path/to/your-project/.qwen
cp -R skills /path/to/your-project/.qwen/skills
```

Then restart Qwen Code inside the target repository and run:

```text
/skills
```

You should see the CloudPort skills listed.

### Option 2: Install as personal skills

Copy the skills into your user-level Qwen skills directory:

```bash
mkdir -p ~/.qwen/skills
cp -R skills/* ~/.qwen/skills/
```

Then restart Qwen Code in any project and run:

```text
/skills
```

The skills should now be available across projects.

### Demo prompt

The full demo prompt is also available at [`docs/demo-prompt.md`](docs/demo-prompt.md).

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

### Expected flow

1. Qwen Code detects relevant CloudPort skills.
2. The agent scans the repository and drafts a migration plan.
3. The human approves the plan.
4. The agent proposes minimal file diffs.
5. The human approves each diff.
6. The agent runs or describes validation checks.
7. The agent provides deploy advice for Alibaba Cloud Function Compute.
8. The human executes deployment actions.

---

## Real-world result: SoccerScope

CloudPort Agent is based on a real migration, not a toy example. SoccerScope is a production YouTube analytics and multilingual comment-analysis pipeline originally built on Gemini and Google Cloud and migrated to Qwen / DashScope and Alibaba Cloud Function Compute.

| Evidence | Link |
|---|---|
| Original Gemini repository | https://github.com/webbigdata-jp/soccerscope |
| Original Gemini web app | https://soccer.tubesaku.com/ |
| Migrated Qwen repository | https://github.com/webbigdata-jp/qwen-soccerscope |
| Migrated Qwen web app | https://qwen-soccer.tubesaku.com/ |
| Qwen embedding API usage | https://github.com/webbigdata-jp/qwen-soccerscope/blob/main/pipeline/1_embed_videos.py#L109 |
| Qwen analysis API usage | https://github.com/webbigdata-jp/qwen-soccerscope/blob/main/pipeline/3_analyze_comments.py#L177 |
| Alibaba Cloud deploy.sh | https://github.com/webbigdata-jp/qwen-soccerscope/blob/main/app/deploy.sh#L25 |
| Demo video | [CloudPort Agent](https://youtu.be/Q7YraU36X0Q) |

Demo measurement from the recorded migration run:

| Metric | Result |
|---|---:|
| End-to-end demo time | About 5 minutes |
| Human approvals | 8 |
| Files changed | 2 |

The migrated app uses:

- **Alibaba Cloud Function Compute** for the SoccerScope web app deployment.
- **Qwen Cloud / DashScope** as the inference backend: `qwen-plus` for analysis and `text-embedding-v4` for retrieval embeddings.
- **MongoDB Atlas Vector Search** for stored videos and vector retrieval.
- **Local pipeline scripts** for data ingestion, embedding, and scheduled jobs.
- **ADK agent structure** (`google.adk.agents`) in the agent layer, which gives CloudPort a practical path to support other ADK-based model backends later.

The agent's brain also runs on Alibaba Cloud through Qwen Code / Qwen Cloud, while the deployed application calls Alibaba Cloud-hosted Qwen APIs at runtime.

---

## Human-in-the-loop and autonomy roadmap

CloudPort Agent is deliberately an advisor before it becomes an operator.

Today, it can scan a repository, produce a migration plan, generate patches, validate the result, and write deployment checklists. It does not silently execute billing-scoped cloud operations or authentication-scoped deployment actions. That boundary is intentional for a migration tool: cloud spend, credentials, production redeploys, and vector-index rebuilds require explicit human approval.

The same skills are written so they can graduate from advisor to supervised operator later. Deployment checklists are structured as machine-followable steps. As agent-operated tooling, scoped cloud credentials, and Qwen Code computer-use capabilities mature, the `deploy-alibaba-fc-advisor` skill can move from "tell the human exactly what to run" to "run this approved step and report back" without changing the overall architecture.

The ADK-based agent layer also gives CloudPort a broader portability path. The reference migration uses `google.adk.agents`, so future ports to other model backends that keep an ADK-like agent structure should require fewer changes than a completely different framework.

---

## Demo video

TODO: Add YouTube link after final recording/editing.

Suggested README embed format after upload:

```md
[![CloudPort Agent demo](docs/architecture_1_migration_overview.png)](TODO_YOUTUBE_URL)
```

---

## Repository layout

```text
cloudport-agent/
├── skills/
│   ├── gemini-to-qwen-api-mapping/
│   ├── dependency-migration/
│   ├── migration-validation/
│   ├── project-profile-generator/
│   ├── deploy-alibaba-fc-advisor/
│   └── project-soccerscope/
├── docs/
│   ├── architecture_1_migration_overview.png
│   ├── architecture_2_skills_architecture.png
│   ├── architecture_3_runtime_layout.png
│   ├── SKILLS_ARCHITECTURE.md
│   └── demo-prompt.md
├── .qwen/
│   └── skills/
├── README.md
└── LICENSE
```

Recommended repository setup:

- Keep `skills/` as the canonical source for distribution.
- Copy the same content into `.qwen/skills/` so opening Qwen Code at the repository root works immediately.
- Avoid symbolic links because they can behave differently across operating systems and ZIP downloads.

---

## Pre-submission checklist

Before submitting to Devpost:

- [ ] `skills/` and `.qwen/skills/` contain the final six skills.
- [ ] Dependency file layout guidance is reflected in `dependency-migration`.
- [ ] README links work, except the intentionally pending YouTube link before upload.
- [ ] Architecture images render in GitHub and Devpost.
- [ ] Demo-time and approval-count badges match the measured values from the recording.
- [ ] GitHub permalinks point to the exact lines where `pipeline/1_embed_videos.py` and `pipeline/3_analyze_comments.py` call Alibaba Cloud / DashScope APIs.

---

## Built with

Qwen Code, Qwen Cloud, `qwen-plus`, `text-embedding-v4`, DashScope OpenAI-compatible API, Alibaba Cloud Function Compute, Python, OpenAI SDK, Pydantic, MongoDB Atlas Vector Search, Google ADK (`google.adk.agents`), uv, mcp, rag, mongodb-atlas, dashscope, function-compute, alibaba-cloud, agent-skills, python 

---

## License

This project is released under the Apache License 2. See [`LICENSE`](LICENSE).
