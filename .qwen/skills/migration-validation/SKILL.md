---
name: migration-validation
description: Verify behavioral equivalence after porting Gemini applications to Qwen, including text, image, video, thinking modes, structured output, embeddings, UI rendering, deployment ZIPs, and Function Compute smoke tests. Use after every migration edit and before declaring a port complete.
---

# Migration Validation

A migration is complete only when static, request-shape, behavioral, packaged,
and deployed checks are accounted for. Report each check as PASS, FAIL, or
NOT RUN with the reason; never turn account-dependent checks into assumed PASS.

## 1. Static and clean-environment checks

- Direct Gemini imports/calls are absent from intended ported paths.
- Remaining Google imports are classified as unrelated, retained provider
  paths, or migration misses.
- Old environment variables are not read by the new path.
- Dependency resolution and installation succeed from a clean environment.
- Syntax/compile tests and existing unit tests pass.
- `skills/` and `.qwen/skills/` mirrors are byte-identical when the repository
  uses that convention.

## 2. Request-shape unit tests

Mock the provider client and assert the exact request, not just return text.
Cover:

- ordered text/image/video content parts;
- multiple images and no accidental nested list;
- intended URI sent by each UI action;
- `video_url` and required sampling fields;
- endpoint precedence and region/workspace configuration;
- temperature/range translation;
- response text extraction for supported content shapes;
- Thinking Auto, Manual, and Off;
- manual total output limit greater than the thinking budget.

## 3. Multimodal behavioral matrix

Run the smallest representative matrix:

```text
text  × selected text-capable models
image × each distinct image-routing pattern
video × each distinct video-routing pattern
thinking × Auto / representative Manual budget / Off
runtime × local source / unpacked package / deployed function
```

For every UI action verify:

- no exception is exposed as a raw framework crash;
- a non-empty result is rendered in the correct panel;
- the answer refers to the intended image/video, not merely a plausible asset;
- multi-image answers discuss all required images;
- source/upstream defects discovered during migration have regression coverage.

Read [multimodal-ui-checklist.md](multimodal-ui-checklist.md) when the app has a
browser UI, image/video calls, or selectable thinking.

## 4. Structured output equivalence

- Validate every new response with the shared Pydantic/schema model.
- Use at least 10 varied samples for a production structured-output path.
- Compare field presence, enum/range validity, nullability, and downstream
  acceptance rather than exact prose.
- Test truncation and malformed JSON handling.
- Confirm whether thinking is intentionally disabled or explicitly validated
  with the chosen structured-output mode.

## 5. Embedding sanity

- Actual vector length matches both model configuration and vector index.
- Corpus and query use the same Qwen embedding configuration.
- Old and new vectors are isolated; a complete re-embed/backfill plan exists.
- Self-similarity is approximately 1 and paraphrases rank above unrelated text
  in a small retrieval smoke test.
- Stored records land in the expected new collection/index/schema.

## 6. Deployment artifact checks

Before upload:

- build script syntax and source manifest checks pass;
- archive root contains required entrypoint/bootstrap files;
- development files, secrets, and local environments are excluded;
- entrypoint is executable when required;
- build/runtime Python versions and native-wheel platform match;
- unpacked archive starts locally under the target-style command;
- health endpoint succeeds.

Avoid `producer | grep -q` package validation under `set -o pipefail`; an early
consumer exit can make a successful match look like failure. Write the archive
manifest to a temporary file, then inspect it.

## 7. Live and deployed checks

Account-dependent checks include:

- model availability in the selected region/workspace;
- key/endpoint consistency;
- remote media reachability from Model Studio;
- text, image, and video live smoke calls;
- FC memory, timeout, code-package size, and public/auth settings;
- public UI and health endpoint;
- logs and cost telemetry.

Separate latency observations into provider inference, thinking mode, remote
media fetch, FC cold start, and warm requests. A slow video/Auto-thinking call
is not automatically an application failure, but timeouts and user-visible
behavior must be documented.

## 8. Human sign-off

Present:

1. checklist with PASS/FAIL/NOT RUN;
2. changed-files summary;
3. known source defects fixed separately from provider migration;
4. live evidence and unresolved account-specific risks;
5. rollback point.

Wait for approval before deployment. Deployment advice belongs to
`deploy-alibaba-fc-advisor`.
