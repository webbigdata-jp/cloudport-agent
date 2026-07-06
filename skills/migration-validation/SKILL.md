---
name: migration-validation
description: Verify functional equivalence after porting code from Gemini to Qwen Cloud. Use after ANY migration edit, before declaring a port complete, or when the user asks "did the migration work", "compare outputs", or "validate the port". Never skip this for embedding or structured-output code.
---

# Migration Validation

A port is DONE only when these checks pass. Report results as a
checklist to the human before proceeding to deployment.

## 1. Static checks

- `grep -rn "google.genai"` returns zero hits in ported files.
- Old env var (`GEMINI_API_KEY`) is not read by ported code paths.
- `uv lock` / dependency resolution succeeds from a clean environment.

## 2. Structured output equivalence

- Run the SAME input sample through old and new code (if the old key
  is still available) or through the new code only (if not).
- Validate every response with the shared Pydantic model:
  `Model.model_validate_json(...)` must succeed on N≥10 varied samples.
- Compare field-level distributions, not exact strings: LLM outputs are
  non-deterministic. Check that enum fields stay within the allowed
  set, numeric scores stay in range, and required fields are non-null.

## 3. Embedding sanity

- Dimension check: `len(vec)` matches the new model's documented
  dimension AND the vector index config (e.g. MongoDB Atlas
  `numDimensions`).
- Self-similarity smoke test: cosine(v, v) ≈ 1.0; cosine of two
  unrelated texts is meaningfully lower than two paraphrases.
- Confirm the corpus re-embed backfill plan exists (old Gemini vectors
  must not remain mixed in the same index).

## 4. Pipeline smoke run

- Run the smallest end-to-end slice (e.g. 1 day of data, or a
  `--limit 5` flag) and confirm records land in the datastore with the
  expected schema.
- Check cost telemetry after the smoke run in the Qwen Cloud console —
  confirms billing wiring AND produces a screenshot-able cost view.

## 5. Human sign-off

Present the checklist results and the diff summary to the human and
wait for approval before any deployment step. Deployment advice is
handled by the `deploy-alibaba-fc-advisor` skill — do not deploy
directly from this skill.
