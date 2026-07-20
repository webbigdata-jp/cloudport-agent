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

## 4. Semantic routing checks

A 200 response is not enough. Verify the model received the intended asset:

- ER/architecture diagram response mentions entities/relationships.
- Two-image comparison discusses both images.
- Video description, tags, highlights, and geolocation use their own videos.
- No call contains a nested Python list serialized as text.
- The rendered response is non-empty.

The validated example caught upstream-style defects where an ER response was
not rendered and the glasses tab sent the ER image. Keep these as regression
patterns, not project-specific rules.

## 5. Current sources to verify during a migration

- OpenAI-compatible chat and thinking parameters:
  https://www.alibabacloud.com/help/en/model-studio/qwen-api-via-openai-chat-completions
- Image and video understanding payloads:
  https://www.alibabacloud.com/help/en/model-studio/vision
- Regional/workspace endpoints:
  https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- Golden migration example:
  `examples/gemini-streamlit-cloudrun-to-qwen-fc/`
