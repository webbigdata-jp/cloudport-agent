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

## Known field lessons (Function Compute)

- npx-at-runtime is forbidden: FC cold-start timeouts kill
  `npx -y <package>` style runtime fetches. Pre-fetch/pre-install at
  image build time. (Note: this constraint is FC-specific — the same
  Dockerfile pattern is fine on platforms without this timeout.)
- Confirm region + account type (intl vs mainland) before writing any
  endpoint or console URL into the checklist.
- Environment variables (`DASHSCOPE_API_KEY`, datastore URIs) go into
  FC service config, never into the image.

## Checklist template for the human

1. Pre-deploy: validation checklist from `migration-validation` is
   fully green; image builds locally; env vars listed with sources.
2. Deploy: exact commands with placeholders resolved, expected output
   after each command, and the single console screen to verify.
3. Post-deploy: one smoke request + expected response; where to see
   logs; where to see cost telemetry (screenshot this for the record).
4. Rollback: the one-liner to revert to the previous version, written
   down BEFORE deploying.

Deliver the checklist to the human as a single copy-pasteable block
and wait. Do not proceed on their behalf.
