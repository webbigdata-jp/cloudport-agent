---
name: system-diagram-generator
description: Scan an already-cloned repository and generate a self-contained HTML report with system architecture diagrams (infrastructure/deployment diagram, data flow diagram) plus a system-scale summary. Use when the user asks to "draw a system diagram", "visualize this repo's architecture", "explain the overall structure of this codebase", or needs an estimation-ready overview of an unfamiliar / inherited project for outsourcing or handover. Standalone skill — does NOT require the Gemini-to-Qwen migration flow.
---

# System Diagram Generator

Turns an unfamiliar repository into a shareable architecture report:
one HTML file containing an infrastructure/deployment diagram, a data
flow diagram, and a scale summary — enough for a third party (e.g. an
outsourcing vendor at the estimation stage, before an NDA is signed)
to grasp the system's shape and size WITHOUT seeing the source code
or any confidential detail.

## Preconditions

- The target repository is ALREADY cloned locally and Qwen Code is
  running at (or given the path to) its root. This skill never runs
  `git clone` and never needs GitHub credentials.
- Output is ONE fully self-contained HTML file, designed to be sent
  as an email attachment. The recipient needs only a web browser: no
  internet connection, no extra software, no companion files. No
  PNG/SVG export.

## Output language

Write the report in **English by default**. If the user is conversing
in another language (e.g. Japanese), write the report in that language
instead, keeping technology names (S3, Cloud Run, ...) as-is.

## Confidentiality rules (apply to EVERYTHING in the report)

The report may be shown outside the company. Before writing any text
into the HTML, sanitize:

- NEVER include: secret values, API keys, tokens, passwords,
  connection strings, `.env` contents, internal hostnames/IPs/ports,
  cloud account IDs, ARNs, project IDs, real bucket/queue/DB/cluster
  names, customer names, or business-specific proper nouns.
- NEVER include source code excerpts, file contents, or verbatim
  comments. File and directory NAMES may appear only when generic
  (`pipeline/`, `api/`); rename anything revealing
  (`acme_bank_export.py` → "batch export script").
- Env vars: names may be listed only if generic (`DATABASE_URL`);
  values never.
- Generalize resources: write "Object storage bucket (static assets)"
  not the actual bucket name; "PostgreSQL (RDS)" not the instance id.
- Final self-check: re-read the finished HTML once, specifically
  hunting for identifiers that leak. Fix before presenting.

## Scan procedure (staged — do not read every file)

1. **Shape**: directory tree 2–3 levels deep; README/docs if present
   (background info only — verify claims against code).
2. **Dependencies**: `package.json`, `pyproject.toml`,
   `requirements*.txt`, `go.mod`, `pom.xml`, `Gemfile`, lockfiles.
   Note languages, frameworks, cloud SDKs.
3. **Infra as code / deploy** (→ *confirmed* evidence): Terraform
   (`*.tf`), CloudFormation/SAM/CDK, `serverless.yml`, `app.yaml`,
   Bicep/ARM, Kubernetes manifests, Helm charts, `Dockerfile`,
   `docker-compose*`, CI/CD configs (`.github/workflows`,
   `cloudbuild.yaml`, `azure-pipelines.yml`), Procfile.
4. **Cloud/service usage in code** (→ *inferred* evidence): SDK
   imports (`boto3`, `aws-sdk`, `google-cloud-*`, `@azure/*`,
   `firebase-admin` ...), client instantiations, env var NAMES
   (`AWS_*`, `AZURE_*`, `GCP_*`, `*_BUCKET`, `*_QUEUE`, `REDIS_URL`,
   `DATABASE_URL`), well-known endpoints in config.
5. **Entry points & flow**: main/handler/`index.*`, web framework
   routes, cron/queue workers, shell scripts, CI-triggered jobs.
   Establish the order data moves: ingress → processing → storage →
   egress, including external SaaS APIs called.
6. **Metrics**: per-language file count and LOC. Use `cloc . --json`
   if available; otherwise fall back to `find` + `wc -l` grouped by
   extension (exclude `.git`, `node_modules`, `vendor`, lockfiles,
   build output). Count: source files, LOC by language, direct
   dependencies, entry points, external services, cloud resources.

Qwen3-class context is large, but stay staged: read manifests and
infra files fully; sample only representative source files (entry
points, one file per major module) — never bulk-read the tree.

## Evidence labels: confirmed vs inferred

Every cloud resource / external service gets a confidence label:

- **confirmed** — declared in IaC, deploy config, manifests, CI, or
  Dockerfiles.
- **inferred** — deduced from SDK imports, env var names, or code
  patterns only. Real infra may differ; say so.

In Mermaid: solid borders/arrows for confirmed, dashed
(`stroke-dasharray` via `classDef`, `-.->` edges) for inferred.
Always render the legend explaining both.

## Diagrams (Mermaid, rendered inside the HTML)

Use `flowchart` (most reliable to render). Keep each diagram under
~25 nodes; collapse detail into grouped nodes rather than omitting
whole subsystems.

1. **Infrastructure / deployment diagram** — `subgraph` per
   environment/provider (AWS / GCP / Azure / on-prem / SaaS), nodes
   for each service actually used (e.g. Lambda, Function Compute,
   Cloud Run, S3, RDS, Pub/Sub), plus user/client and CI/CD entry.
   Name provider-specific services explicitly — that is what makes
   migration cost visible.
2. **Data flow diagram** — sources → ingestion → processing/compute →
   stores (DB, cache, object storage, vector index) → consumers.
   Label edges with the KIND of data (e.g. "video metadata",
   "embeddings"), never actual values or record samples.

## HTML report

Start from `template.html` in this skill's directory (read it with
the file-read tool relative to this SKILL.md). Fill the placeholders;
keep its structure:

1. Title, generation date, repo described generically, disclaimer
   ("generated by static analysis; inferred items unverified").
2. System overview — 5–10 sentences: purpose (as far as code reveals
   it, phrased generically), tech stack, runtime model.
3. Infrastructure/deployment diagram + legend.
4. Data flow diagram.
5. Cloud & external services inventory table: service / provider /
   role / evidence (confirmed|inferred) / migration notes
   (provider-specific = porting cost signal).
6. Scale summary table (metrics from step 6) + a one-paragraph
   complexity read-out (e.g. "mid-size: ~12k LOC Python across 3
   deployable units, 5 external services, 2 datastores").
7. Assumptions & open questions — everything a vendor would need to
   ask before quoting.

**Make the file self-contained.** The template contains a
`<!-- MERMAID_JS_HERE -->` marker. Download Mermaid once at
generation time and inline it there:

```
curl -sL -o /tmp/mermaid.min.js \
  https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js
```

(if curl/CDN is unreachable, `npm install mermaid@11` and use
`node_modules/mermaid/dist/mermaid.min.js`), then splice the file
contents into a `<script>...</script>` block at the marker — do this
with a small script, never by pasting ~3.5 MB of JS through the model
context, and escape any `</script>` inside it as `<\/script>`.
Verify the result: the final HTML must contain NO external
`src`/`href` references, and total size stays under ~4 MB — fine for
an email attachment. Only if the download
fails (offline generation environment), fall back to
`<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>`
and warn the user that recipients will then need internet access to
see the diagrams.

Write the file to `system-diagram.html` in the current working
directory (or a user-specified path). Do not modify the target
repository.

## Human-in-the-loop

1. After scanning, present a short findings summary (detected stack,
   cloud services with labels, planned diagram scope) and confirm
   before generating the HTML.
2. After generating, tell the human to review the HTML themselves for
   confidential leakage before sharing it externally — the skill's
   sanitization is best-effort, the human sign-off is the gate.
