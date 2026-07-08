# CloudPort Agent — Skills Architecture

CloudPort Agent packages real production migration know-how
(**Gemini / GCP → Qwen / Alibaba Cloud**) as **Qwen Code Agent Skills** —
Qwen Code's native extension format (`.qwen/skills/`, model-invoked,
git-shareable).

The reference migration is SoccerScope, a production YouTube analytics
and multilingual comment-analysis app. The original version runs on
Gemini / GCP assumptions; the migrated version runs on Qwen / DashScope
and Alibaba Cloud Function Compute.

- Original Gemini repository: https://github.com/webbigdata-jp/soccerscope
- Original Gemini web app: https://soccer.tubesaku.com/
- Migrated Qwen repository: https://github.com/webbigdata-jp/qwen-soccerscope
- Migrated Qwen web app: https://qwen-soccer.tubesaku.com/

## Three-part architecture

### 1. Migration overview

CloudPort Agent sits between the source stack and the target stack:

```text
GCP with Gemini
    |
    | migration input
    v
CloudPort Agent inside Qwen Code
    |
    | uses CloudPort Skills
    v
Qwen with Alibaba Cloud
```

The migration copilot scans the repository, drafts a plan, proposes
patches, validates the result, and advises on deployment.

The reference agent layer uses ADK (`google.adk.agents`). This is
important for future portability: because CloudPort Skills encode
migration rules, validation constraints, and deployment guidance rather
than only project-specific code, they should be relatively easy to
adapt to other model backends that also use ADK-style agent structure.

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
    └── your-project/
```

Supporting a new project means adding one thin profile skill. The core
skills remain stable. `project-profile-generator` drafts that profile
automatically; a human approves it before migration proceeds.

See: [`architecture_2_skills_architecture.png`](architecture_2_skills_architecture.png)

### 3. What runs where after migration

```text
Local machine
├── Qwen Code + CloudPort Skills
├── pipeline scripts
└── run_daily.sh
       │
       ├── calls Qwen Cloud / DashScope APIs
       └── writes videos and embeddings to MongoDB Atlas

Alibaba Cloud
├── Function Compute
│   └── SoccerScope app, uploaded as a console ZIP package
└── Qwen Cloud / DashScope
    ├── qwen-plus
    └── text-embedding-v4

MongoDB Atlas
└── videos collection + vector index
```

The agent's brain also runs on Alibaba Cloud through Qwen Code / Qwen
Cloud, while the migrated application calls Alibaba Cloud-hosted Qwen
APIs at runtime.

See: [`architecture_3_runtime_layout.png`](architecture_3_runtime_layout.png)

## Human-in-the-loop gates

CloudPort Agent uses three explicit approval gates:

1. **Plan approval** — the agent scans the repository and proposes a
   migration plan before editing files.
2. **Diff approval** — every file change is presented as a patch for
   human review.
3. **Deployment approval** — deployment remains advisory by default;
   the human executes billing-scoped and credential-scoped actions.

The recorded demo run took about **5 minutes**, required **8 human
approvals**, and changed **2 files**.

## Real migration evidence

| Evidence | Link |
|---|---|
| Original Gemini repository | https://github.com/webbigdata-jp/soccerscope |
| Original Gemini web app | https://soccer.tubesaku.com/ |
| Migrated Qwen repository | https://github.com/webbigdata-jp/qwen-soccerscope |
| Migrated Qwen web app | https://qwen-soccer.tubesaku.com/ |
| Qwen embedding API usage | https://github.com/webbigdata-jp/qwen-soccerscope/blob/main/pipeline/1_embed_videos.py#L112 |
| Qwen analysis API usage | https://github.com/webbigdata-jp/qwen-soccerscope/blob/main/pipeline/3_analyze_comments.py#L180 |

## Why native Skills instead of a custom framework

- **Advanced use of custom skills:** CloudPort uses Qwen Code's
  first-class mechanism: model-invoked triggering, `/skills`,
  paths-gated project profiles, and progressive disclosure through
  `SKILL.md` plus examples/reference files.
- **Readable migration knowledge:** API mappings, embedding warnings,
  Function Compute constraints, ADK assumptions, and validation rules
  are stored as Markdown that can be reviewed and improved.
- **Distribution:** project skills live in the repository, so the OSS
  community can fork CloudPort and add profiles for their own stacks.
- **Debuggability:** if the agent gives wrong advice, the skill can be
  edited, committed, reviewed, and re-run.
- **Future portability:** because the reference agent layer uses ADK
  (`google.adk.agents`), the same skill structure should be reusable
  for other ADK-based model backends with less work than a full rewrite.
