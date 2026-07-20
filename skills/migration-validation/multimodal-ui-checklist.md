# Multimodal UI validation checklist

Use this as a concrete acceptance matrix, adapting rows to the application.

## Offline

- [ ] converter preserves ordered text/media parts
- [ ] image URI maps to `image_url`
- [ ] video URI maps to `video_url` with validated sampling parameters
- [ ] multiple images remain separate parts
- [ ] nested lists are rejected/flattened defensively and source call is fixed
- [ ] Auto omits thinking override
- [ ] Manual sends enabled thinking and budget
- [ ] Off sends disabled thinking
- [ ] answer budget and total completion budget are not confused
- [ ] Qwen parameter boundaries are reflected in UI and adapter (`temperature < 2`, valid `top_p`)
- [ ] every generation call has an explicit intended config/thinking policy
- [ ] response extraction handles empty/non-string content intentionally

## Live API

- [ ] text smoke request returns a relevant non-empty answer
- [ ] image smoke request describes the supplied image
- [ ] video smoke request describes the supplied video
- [ ] key and base URL are from the same workspace/region
- [ ] provider can fetch the remote media URL
- [ ] representative Manual budget does not violate total output limit

## Browser/UI

- [ ] every button renders output in its own response panel
- [ ] generated responses are actually rendered (`st.markdown`/equivalent), not only assigned
- [ ] diagram action discusses the diagram and its response is visible
- [ ] multi-image action discusses all supplied images
- [ ] no action receives another tab's stale config or media URI
- [ ] if Thinking is presented as global, image/video calls also receive it; otherwise the UI clearly scopes it
- [ ] errors are caught and shown with provider-appropriate diagnostics
- [ ] framework-generated error helper links do not misbrand the provider

## Package/runtime

- [ ] official FC runtime list/region supports the chosen Python minor
- [ ] exact `deploy.sh` runs end-to-end and prints its final success marker
- [ ] source launch works
- [ ] server/health can start without making a live provider request
- [ ] unpacked ZIP imports and launch work in target-compatible Linux/architecture/Python
- [ ] all native extensions match the target, not just one sampled file
- [ ] health endpoint returns success
- [ ] compressed ZIP size fits the selected region/upload method
- [ ] public Function Compute URL works
- [ ] cold and warm latency are recorded separately

## Evidence labels

- [ ] binary-format inspection is not reported as unpacked-package PASS
- [ ] manually replayed build commands are not reported as deploy-script PASS
- [ ] account-dependent and target-environment checks are PASS/FAIL/NOT RUN separately

Golden acceptance evidence:
`examples/gemini-streamlit-cloudrun-to-qwen-fc/docs/TESTING.md`.
