# Integration into `cloudport-agent`

## Recommendation

Add this as a complete migration example and update the existing API mapping,
dependency migration, validation, and Alibaba FC deployment skills. It should
not become a separate top-level skill: its reusable knowledge belongs to those
existing capabilities.

## Proposed layout

```text
cloudport-agent/
├── examples/
│   └── gemini-streamlit-cloudrun-to-qwen-fc/
│       ├── app.py
│       ├── cloudport_compat.py
│       ├── requirements.txt
│       ├── deploy.sh
│       ├── smoke_test.py
│       ├── tests/
│       │   └── test_cloudport_compat.py
│       ├── docs/
│       │   ├── MIGRATION.md
│       │   ├── TESTING.md
│       │   └── REPO_INTEGRATION.md
│       ├── README.md
│       └── .gitignore
├── skills/
└── .qwen/skills/
```

Do not add `main.py`, `pyproject.toml`, or dated `TEST_RESULTS.md` to this
example. `requirements.txt` is the sole runtime dependency declaration.

## Reusable skill updates

### Gemini-to-Qwen API mapping

- classify each call as text, image, video, structured output, long-context, or
  reasoning-heavy before selecting a target model;
- do not mechanically translate model IDs from a static table;
- when one global selector drives every modality, expose only models supporting
  every used modality;
- map image URI to `image_url` and video URI to `video_url` plus `fps`;
- map Thinking Off to `enable_thinking=false`;
- place Qwen-only fields in `extra_body` when using the OpenAI SDK;
- account for parameter-domain differences;
- use a narrow compatibility module when many call sites share the same source
  SDK surface.

### Dependency migration

- remove `google-genai` only when that dependency is actually replaced;
- do not remove unrelated Google packages by name prefix;
- keep one dependency source of truth for a standalone example;
- validate target OS, architecture, and Python ABI for ZIP deployments.

### Migration validation

Validate a matrix covering:

```text
text × selected models
image × visual model
video × visual model
thinking Auto / Manual / Off
local process / packaged process / FC process
```

Check payload shape, intended media, non-empty rendered UI output, endpoint/key
consistency, remote asset reachability, health endpoint, and known negative
cases. The ER and glasses defects show why import-only validation is
insufficient.

### Alibaba FC deployment advisor

Document the Streamlit Web Function pattern:

- root-level executable `bootstrap`;
- bind `0.0.0.0` and read `FC_CUSTOM_LISTEN_PORT`;
- writable `/tmp` home fallback;
- Linux x86_64 wheel build or an explicitly verified alternative;
- archive-root validation;
- `/_stcore/health` checks before and after deployment;
- distinction between upload-size errors and startup errors.

## Implementation sequence

1. Add the example directory.
2. Run offline unit tests.
3. Run live text/image/video smoke tests in one region.
4. Build and inspect `code.zip` on Linux x86_64.
5. Update canonical skill files under `skills/`.
6. Synchronize the repository's mirrored `.qwen/skills/` copies.
7. Update the repository example index.
8. Deploy and attach public evidence only after live validation.

## Definition of done

- offline tests pass;
- live text/image/video smoke tests pass in a documented workspace;
- all Streamlit tabs render the intended result;
- `deploy.sh` produces a root-layout ZIP without development files;
- FC health and public UI checks pass;
- canonical and mirrored skill copies are synchronized.
