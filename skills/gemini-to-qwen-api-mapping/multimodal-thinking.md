# Multimodal and thinking migration reference

Read this reference when a Gemini application uses `Part.from_uri`, images,
videos, a global model picker, or `ThinkingConfig`.

## 1. Classify call sites first

Create a table before editing:

| Call site | Inputs | Output | Thinking | Structured | Candidate target |
|---|---|---|---|---|---|
| freeform | text | text | selectable | no | text/reasoning model |
| image compare | multiple images + text | text/table | selectable | no | visual model |
| video tags | video + text | table | selectable | no | video-capable visual model |

A global model picker is valid only when every listed model supports every row.
Otherwise split the picker or select models internally per call site.

Also record the configuration source for every row. If Thinking is global, each
call must receive an explicit `thinking_config`/request policy. A bare call that
omits `config` is not equivalent merely because the selected model has a default
Thinking mode. Avoid reusing a `config` variable created in another Streamlit
tab; build a call-local config or a named shared helper.

## 2. Ordered content conversion

```python
def to_openai_content(contents):
    if isinstance(contents, str):
        return [{"type": "text", "text": contents}]

    parts = []
    for item in contents:
        if isinstance(item, Part):
            parts.append(item.payload)
        elif isinstance(item, (list, tuple)):
            # Defensive only: also fix and test the nested source call site.
            parts.extend(to_openai_content(item))
        else:
            parts.append({"type": "text", "text": str(item)})
    return parts
```

Image and video adapters:

```python
@dataclass(frozen=True)
class Part:
    payload: dict

    @classmethod
    def from_uri(cls, file_uri: str, mime_type: str):
        if mime_type.startswith("image/"):
            return cls({
                "type": "image_url",
                "image_url": {"url": file_uri},
            })
        if mime_type.startswith("video/"):
            return cls({
                "type": "video_url",
                "video_url": {"url": file_uri},
                "fps": 2,
            })
        raise ValueError(f"Unsupported URI MIME type: {mime_type}")
```

Do not silently turn unknown binary parts into `str(item)`.

## 3. Thinking translation

```python
extra_body = {}

if thinking_budget is None:
    pass  # Auto/model default
elif thinking_budget <= 0:
    extra_body["enable_thinking"] = False
else:
    extra_body["enable_thinking"] = True
    extra_body["thinking_budget"] = thinking_budget
```

If the UI separately controls answer tokens:

```python
THINKING_TOKEN_SAFETY_MARGIN = 16


def total_output_limit(answer_tokens, thinking_budget):
    if answer_tokens is None:
        return None
    if thinking_budget and thinking_budget > 0:
        return answer_tokens + thinking_budget + THINKING_TOKEN_SAFETY_MARGIN
    return answer_tokens
```

Required boundary tests:

- Auto omits Qwen thinking fields.
- Manual sends both fields.
- Off sends `enable_thinking=false`.
- Manual total output limit is greater than the thinking budget.
- The UI label distinguishes answer tokens from total completion tokens.

## 4. Sampling boundary translation

Gemini and Qwen ranges are not identical. Current Qwen documentation specifies:

- `temperature`: `[0, 2)` — never send exactly `2.0`;
- `top_p`: greater than zero and at most 1 for OpenAI-compatible chat.

Reflect this in the UI and validate in the adapter. Unit-test the upper/lower
boundaries, not only a normal value such as 0.7.

## 5. Semantic routing checks

A 200 response is not enough. Verify the model received the intended asset:

- ER/architecture diagram response mentions entities/relationships.
- Two-image comparison discusses both images.
- Video description, tags, highlights, and geolocation use their own videos.
- No call contains a nested Python list serialized as text.
- The rendered response is non-empty and the render statement exists in the
  button's response branch.
- Every call receives the intended config/thinking policy.
- Provider errors are caught at the UI boundary rather than shown as raw
  Streamlit tracebacks.

The validated example caught upstream-style defects where an ER response was
not rendered and the glasses tab sent the ER image. Keep these as regression
patterns, not project-specific rules.

## 6. Current sources to verify during a migration

- OpenAI-compatible chat and thinking parameters:
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions
- Image and video understanding payloads:
  https://www.alibabacloud.com/help/en/model-studio/vision
- Regional/workspace endpoints:
  https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- Golden migration example:
  `examples/gemini-streamlit-cloudrun-to-qwen-fc/`
