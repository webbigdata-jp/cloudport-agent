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
- [ ] diagram action discusses the diagram
- [ ] multi-image action discusses all supplied images
- [ ] no action receives another tab's stale config or media URI
- [ ] errors are caught and shown with provider-appropriate diagnostics
- [ ] framework-generated error helper links do not misbrand the provider

## Package/runtime

- [ ] source launch works
- [ ] unpacked ZIP launch works with target-style Python/port variables
- [ ] health endpoint returns success
- [ ] public Function Compute URL works
- [ ] cold and warm latency are recorded separately

Golden acceptance evidence:
`examples/gemini-streamlit-cloudrun-to-qwen-fc/docs/TESTING.md`.
