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
