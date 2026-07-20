# CloudPort Agent — Skills Architecture

CloudPort Agent packages production migration know-how (**Gemini / GCP → Qwen / Alibaba Cloud**) as native, model-invoked Qwen Code Agent Skills.

The reference migration is SoccerScope, a production YouTube analytics and multilingual comment-analysis application. The original version runs on Gemini / GCP assumptions; the migrated version runs on Qwen / DashScope and Alibaba Cloud Function Compute.

- Original Gemini repository: https://github.com/webbigdata-jp/soccerscope
- Original Gemini web app: https://soccer.tubesaku.com/
- Migrated Qwen repository: https://github.com/webbigdata-jp/qwen-soccerscope
- Migrated Qwen web app: https://qwen-soccer.tubesaku.com/
- In-repository runnable example: ../examples/gemini-streamlit-cloudrun-to-qwen-fc/

## Three-part architecture

### 1. Supervised migration operator

```text
Gemini / GCP repository
        |
        v
CloudPort Agent inside Qwen Code
        |
        ├── automatic discovery and project profile
        ├── automatic code / dependency migration
        ├── automatic tests, diagnosis, and repair
        └── automatic FC artifact build and validation
        |
        v
Human cloud boundary
        |
        ├── production credentials
        ├── resource / instance creation
        ├── billable vector-index rebuilds
        └── production deployment
        |
        v
Qwen + Alibaba Cloud runtime
```

CloudPort Agent is an operator inside the checked-out repository. It does not require separate human approval for the plan or each diff. Qwen Code's selected approval mode remains the local safety layer: routine edits and tests can proceed automatically, while destructive shell commands and other risky operations are blocked or require an operator decision.

Cloud resource creation and production deployment remain manual by design because they can change spend, credentials, or availability.

See: [`architecture_1_migration_overview.png`](architecture_1_migration_overview.png)

### 2. Skills architecture

```text
.qwen/skills/
│
├── CORE
│   ├── gemini-to-qwen-api-mapping/
│   ├── dependency-migration/
│   ├── migration-validation/
│   └── deploy-alibaba-fc-advisor/
│
├── GENERALIZER
│   └── project-profile-generator/
│
└── PROJECT PROFILES
    ├── project-soccerscope/
    └── project-<new-repository>/
```

For an unfamiliar repository, `project-profile-generator` scans Python, JavaScript / TypeScript, SDK, REST, configuration, dependency, CI, infrastructure, and deployment surfaces. It writes a thin, reviewable project profile and continues the repository migration unless a concrete high-impact ambiguity prevents safe progress.

The profile is an audit artifact and routing mechanism, not a mandatory human stop. The core skills remain stable while each repository adds a thin profile.

`system-diagram-generator` is a standalone discovery and handover tool. It is useful before a migration but is not part of the migration execution dependency chain.

See: [`architecture_2_skills_architecture.png`](architecture_2_skills_architecture.png)

### 3. What runs where after migration

```text
Local machine
├── Qwen Code + CloudPort Skills
├── pipeline scripts
└── scheduled jobs
       │
       ├── call Qwen Cloud / DashScope APIs
       └── write data and embeddings to MongoDB Atlas

Alibaba Cloud
├── Function Compute
│   └── application uploaded as a self-contained package
└── Model Studio / DashScope
    ├── Qwen text or multimodal model
    └── text-embedding-v4

MongoDB Atlas
└── collection + vector index
```

The agent runtime uses Qwen Code / Qwen Cloud, while the migrated application calls Alibaba Cloud-hosted Qwen APIs at runtime.

See: [`architecture_3_runtime_layout.png`](architecture_3_runtime_layout.png)

## Autonomy and safety model

| Work | Executor | Safety boundary |
|---|---|---|
| Repository inventory and project profile | Agent | Read-only / in-workspace |
| Migration plan | Agent | Reviewable artifact; no mandatory pause |
| Code, config, and dependency edits | Agent | Qwen Code approval mode |
| Tests, diagnosis, and repair | Agent | Qwen Code command classifier / permissions |
| FC package build and validation | Agent | Local artifact only |
| Destructive local operations | Qwen Code + human decision | Blocked or explicitly approved |
| Cloud resource creation and production credentials | Human | Spend / credential boundary |
| Billable index rebuild and production deployment | Human | Spend / availability boundary |

The recorded demonstration took about **5 minutes**, required **8 Qwen Code safety approvals**, changed **2 files**, and required **no human-written code edits**. A separate recent migration test consumed approximately **5.7M input tokens** in total.

## Same-repository Alibaba Cloud evidence

| Evidence | Link |
|---|---|
| Runnable migration example | [`../examples/gemini-streamlit-cloudrun-to-qwen-fc/`](../examples/gemini-streamlit-cloudrun-to-qwen-fc/) |
| Model Studio API compatibility layer | [`cloudport_compat.py`](../examples/gemini-streamlit-cloudrun-to-qwen-fc/cloudport_compat.py) |
| Function Compute package builder | [`deploy.sh`](../examples/gemini-streamlit-cloudrun-to-qwen-fc/deploy.sh) |
| Offline tests | [`tests/test_cloudport_compat.py`](../examples/gemini-streamlit-cloudrun-to-qwen-fc/tests/test_cloudport_compat.py) |
| Live multimodal checks | [`smoke_test.py`](../examples/gemini-streamlit-cloudrun-to-qwen-fc/smoke_test.py) |

A Serverless Devs `s.yaml` is not required for this repository's evidence path. The code directly shows Model Studio request construction and the Function Compute-compatible deployment artifact.

## Why native Skills instead of a custom framework

- **First-class Qwen Code integration:** model-invoked triggering, `/skills`, project profiles, and progressive disclosure through `SKILL.md` and reference files.
- **Readable migration knowledge:** API mappings, embedding warnings, Function Compute constraints, ADK assumptions, and validation rules are reviewable Markdown.
- **Distribution:** project skills live in the repository, so others can fork CloudPort and add profiles for their stacks.
- **Debuggability:** incorrect migration behavior can be traced to a skill, edited, reviewed, and rerun.
- **Portability:** the reference agent layer uses ADK (`google.adk.agents`), so similar agent structures can be migrated without replacing the entire framework.
