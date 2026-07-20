---
name: deploy-alibaba-fc-advisor
description: Advise the human on deploying migrated apps to Alibaba Cloud Function Compute. Use whenever deployment, hosting, "put it on Alibaba Cloud", Function Compute, or go-live comes up after a migration. ADVISORY ONLY — this skill produces commands and checklists for a human to execute; it never runs deployment, billing, or authentication actions itself.
---

# Alibaba Cloud FC Deployment Advisor

## Boundary by design (read first)

Deployment touches BILLING and AUTHENTICATION. By deliberate design,
CloudPort Agent does not execute these actions:

- DO: generate exact commands, console click-paths, config diffs, and
  pre/post-deploy checklists for the human to run.
- DO NOT: run `aliyun`/`s` CLI deploy commands, open browser sessions,
  handle credentials, or accept payment confirmations.

Rationale: cloud-account actions are irreversible and financially
scoped; a human review gate here is cheap insurance. This is a
capability boundary, not a capability gap.

### Autonomy roadmap

When agent-operated browser/console tooling matures (e.g. Qwen Code's
built-in Computer Use) and per-agent scoped cloud credentials with
spend limits become standard, this skill is designed to graduate from
"advisor" to "operator": the checklists below are written as
machine-followable steps precisely so that flipping this skill to
autonomous execution is a frontmatter-and-guardrails change, not a
rewrite.

## Step 0: Does anything need a cloud deploy at all?

Before writing any deployment steps, determine which changed
components are actually cloud-hosted. Read the project profile skill
(`project-*`) for the "what runs where" mapping.

- If the changed files belong to a locally-run component (e.g. batch
  pipeline scripts executed on a workstation/cron), the correct advice
  is: NO cloud redeploy is required. List only the local follow-ups
  (dependency install, env vars) and stop.
- Only produce FC deployment steps for components the profile marks as
  FC-hosted, and only when those components changed.

## Step 1: Determine the deployment method — never assume it

Do NOT invent a deployment mechanism. Docker images + ACR, zip code
packages, Serverless Devs (`s` CLI), and console editing are all valid
FC workflows, and choosing the wrong one produces useless advice.

- The project profile skill defines the method actually used by this
  project. Follow it exactly.
- If the profile does not specify a method, ASK THE HUMAN before
  writing steps. Do not default to Docker.


## Runtime selection gate — never infer it from the source image

Treat these as three separate facts:

1. the source application's Python version (for example, a Cloud Run
   `python:3.13-slim` image);
2. the Python version used to build vendored dependencies;
3. the interpreter actually available in the selected Function Compute runtime
   and region.

They are not automatically equal. Before choosing a ZIP target version, check
the current official FC runtime list and regional availability. As of the FC
Python documentation updated 2026-06-02, the newest listed built-in Python
runtime is Python 3.12 (public preview); Python 3.13 is not listed. Re-check the
documentation during every migration because runtime availability can change.

Do not describe a deployment as "Custom Runtime (Python X.Y)" merely because
the source Dockerfile used X.Y. A Custom Runtime lets the application start its
own HTTP server, but it does not by itself prove that an arbitrary host
interpreter exists. If the source requires a newer Python than FC provides,
choose one of these explicitly and document the tradeoff:

- retarget and test on a supported FC Python version;
- bundle a compatible interpreter/runtime and all required shared libraries;
- use a custom layer with an explicitly configured search path; or
- use a Custom Container based on the required Python image.

Never generate a ZIP whose `bootstrap` hard-requires an executable that has not
been verified in the target FC environment.

Official runtime reference to re-check:
https://www.alibabacloud.com/help/en/functioncompute/fc/python/

## Docker-to-FC zip migration pattern

When the source app was deployed with Docker or Cloud Run and the migrated app
uses FC console zip upload, do not translate the Dockerfile line-by-line. Treat
the Dockerfile as evidence of runtime requirements, then express those
requirements in the FC zip workflow.

### What to extract from the old Dockerfile

Use the old Dockerfile to identify:

- Python runtime version and whether the FC runtime must change.
- Non-Python runtime requirements, especially Node.js for MCP servers.
- Global packages that were pre-installed in the image to avoid runtime fetches.
- Startup command / entrypoint behavior.
- Exposed port assumptions and whether FC injects its own port/handler config.
- Files that were copied into the image.

Then map those into the actual FC deployment method defined by the project
profile.

### FC console zip upload workflow

For projects whose profile says "console zip upload":

1. Build the deployment artifact locally.
2. Vendor Python dependencies into the package root, usually with
   `pip install -t <package-root> -r requirements.txt`.
3. Vendor Node dependencies into the package root if runtime code starts Node
   programs such as an MCP server.
4. Remove unnecessary native payloads or caches only when the project has
   validated that the removed files are not used at runtime.
5. Create the zip from inside the package root, so the function entrypoint files
   are at the top level of the archive.
6. Upload the resulting zip in the FC console.
7. Set secrets and configuration in FC environment variables, not inside the zip.

If a project provides a build script such as `deploy.sh`, prefer the script over
manual reconstruction. The advisor should explain what the script does and where
human review is required, but should not upload the package itself.

### Docker/Cloud Run versus FC zip: common migration differences

| Cloud Run / Docker pattern | FC zip upload pattern |
|---|---|
| Dockerfile defines the runtime image | FC runtime is selected in the console; zip contains code and vendored deps |
| `pip install` runs during image build | `pip install -t build ...` vendors packages into the zip package |
| `npm install -g` can prefetch tools into the image | `npm install --prefix build ...` vendors Node packages into the zip package |
| Container startup uses `CMD` / `$PORT` | FC uses the configured runtime/handler/entrypoint; keep package root layout aligned |
| Image is pushed to a registry or deployed by Cloud Run | `code.zip` is uploaded through FC console or the project's chosen FC workflow |
| Runtime filesystem and caches can be image-backed | Treat runtime as disposable; do not rely on npm/pip cache at startup |

### Advisory wording for zip upload

For a zip-upload project, the deployment response should explicitly say:

- The previous Dockerfile is not the deployment artifact for FC.
- The human should run the project build script locally to produce the zip.
- The human should upload only the generated zip package.
- The human should confirm runtime version, handler, environment variables, and
  attached layers before testing.
- Rollback means re-uploading the previous zip package or switching the FC
  version/alias back, depending on the project's FC setup.

## Streamlit Web Function / Custom Runtime ZIP

When the project profile identifies a Streamlit app deployed as an FC Web
Function with a Custom Runtime ZIP, read
[streamlit-web-function.md](streamlit-web-function.md) before writing the
checklist. This pattern adds requirements beyond an ordinary Python ZIP:

- a root-level executable startup script when the chosen FC setup uses it;
- binding to `0.0.0.0` and `${FC_CUSTOM_LISTEN_PORT}`;
- a writable home/config/cache location under `/tmp`;
- explicit non-development Streamlit mode for target-directory installations;
- runtime-Python discovery and a strict build/runtime minor-version check;
- proof that the chosen Python minor actually exists in the target FC runtime;
- end-to-end execution of the generated build script, not manual replication of
  its internal commands;
- `/_stcore/health` verification for unpacked and deployed artifacts.

Do not apply these Streamlit rules to unrelated frameworks. Treat the project
profile and build script as the source of truth.

## Code-package size and upload-path gate

Measure the final compressed artifact and compare it with the current limit for
the target region and upload method before saying "upload the ZIP". Current FC
documentation distinguishes 500 MB regions from 100 MB regions, and SDK/API
uploads have a separate Base64/request-size constraint. A package that is valid
for Tokyo or Singapore may still be too large elsewhere.

If the artifact is too large, recommend a verified option rather than assuming
console upload will work: remove unused dependencies, split dependencies into a
Layer, use OSS where supported, or switch to a Custom Container. Note that
Custom Runtime layers do not automatically receive Python search-path wiring;
configure `PYTHONPATH`/startup paths explicitly when using them.

Official quota reference to re-check:
https://www.alibabacloud.com/help/en/functioncompute/limits-of-usage

## Known field lessons (Function Compute)

- No runtime package fetches: FC cold-start timeouts kill
  `npx -y <package>`-style on-demand installs. All dependencies must
  be bundled into the deployment artifact ahead of time — inside the
  zip code package (e.g. vendored site-packages / node_modules) or the
  container image, whichever the project uses. (This constraint is
  FC-specific; the same runtime-fetch pattern can be fine on platforms
  without this timeout.)
- Zip-upload specifics: verify the runtime version and handler
  configured on the function match the code package; keep the package
  self-contained (no reliance on pip/npm at startup).
- Confirm region + account type (intl vs mainland) before writing any
  endpoint or console URL into the checklist.
- Environment variables (`DASHSCOPE_API_KEY`, datastore URIs) go into
  FC function/service configuration, never hardcoded into the code
  package or image.

## Checklist template for the human

1. Pre-deploy: validation checklist from `migration-validation` is
   fully green; the deployment artifact (zip package or image, per the
   project's method) is built locally and self-contained; env vars
   listed with sources.
2. Deploy: exact steps for the project's method (console click-path
   for zip upload, or exact commands), expected result after each
   step, and the single console screen to verify.
3. Post-deploy: one smoke request + expected response; where to see
   logs; where to see cost telemetry (screenshot this for the record).
4. Rollback: how to revert to the previous version (previous zip /
   previous image tag / version alias), written down BEFORE deploying.

Deliver the checklist to the human as a single copy-pasteable block
and wait. Do not proceed on their behalf.
