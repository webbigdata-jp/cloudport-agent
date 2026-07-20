"""Compatibility helpers for Gemini-style call sites migrated to Qwen.

The module intentionally mirrors the small subset of ``google-genai`` used by
Google's Streamlit sample: ``Part.from_uri``, ``GenerateContentConfig``,
``ThinkingConfig``, and ``client.models.generate_content``.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Iterable, Mapping, Optional, Union

DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
MAX_QWEN_TEMPERATURE = 1.99
DEFAULT_TIMEOUT_SECONDS = 180.0
# Qwen may account for a few additional internal tokens when validating
# thinking_budget against max_completion_tokens. Alibaba Cloud documents
# that actual counts can differ from max_completion_tokens by up to 10.
THINKING_TOKEN_SAFETY_MARGIN = 16

_WORKSPACE_URL_TEMPLATES = {
    "singapore": "https://{workspace_id}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    "ap-southeast-1": "https://{workspace_id}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    "tokyo": "https://{workspace_id}.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1",
    "ap-northeast-1": "https://{workspace_id}.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1",
    "beijing": "https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    "cn-beijing": "https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    "hong-kong": "https://{workspace_id}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1",
    "hongkong": "https://{workspace_id}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1",
    "cn-hongkong": "https://{workspace_id}.cn-hongkong.maas.aliyuncs.com/compatible-mode/v1",
}

_FIXED_REGION_URLS = {
    "virginia": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    "us-east-1": "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
}


@dataclass(frozen=True)
class ThinkingConfig:
    """Subset of ``google.genai.types.ThinkingConfig`` used by the sample."""

    thinking_budget: Optional[int] = None


@dataclass(frozen=True)
class GenerateContentConfig:
    """Subset of ``google.genai.types.GenerateContentConfig`` used here."""

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    thinking_config: Optional[ThinkingConfig] = None


@dataclass(frozen=True)
class Part:
    """URI-based multimodal part compatible with the sample's call sites."""

    payload: dict[str, Any]

    @classmethod
    def from_uri(cls, file_uri: str, mime_type: str) -> "Part":
        if not file_uri:
            raise ValueError("file_uri must not be empty")
        if not mime_type:
            raise ValueError("mime_type must not be empty")

        if mime_type.startswith("video/"):
            return cls(
                {
                    "type": "video_url",
                    "video_url": {"url": file_uri},
                    "fps": 2,
                }
            )
        if mime_type.startswith("image/"):
            return cls({"type": "image_url", "image_url": {"url": file_uri}})
        raise ValueError(
            f"Unsupported URI MIME type: {mime_type!r}. "
            "This example supports image/* and video/*."
        )


@dataclass(frozen=True)
class _Response:
    text: Optional[str]


def resolve_base_url(environ: Optional[Mapping[str, str]] = None) -> str:
    """Resolve the Model Studio OpenAI-compatible endpoint.

    Precedence:
    1. ``DASHSCOPE_BASE_URL`` (recommended for production)
    2. ``DASHSCOPE_REGION`` + optional ``DASHSCOPE_WORKSPACE_ID``
    3. Legacy Singapore endpoint, retained as a compatibility fallback
    """

    env = os.environ if environ is None else environ
    explicit = env.get("DASHSCOPE_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")

    region = env.get("DASHSCOPE_REGION", "singapore").strip().lower()
    if region in _FIXED_REGION_URLS:
        return _FIXED_REGION_URLS[region]

    workspace_id = env.get("DASHSCOPE_WORKSPACE_ID", "").strip()
    template = _WORKSPACE_URL_TEMPLATES.get(region)
    if workspace_id and template:
        return template.format(workspace_id=workspace_id)

    return DEFAULT_BASE_URL


def _iter_openai_parts(items: Iterable[Any]) -> Iterable[dict[str, Any]]:
    for item in items:
        if isinstance(item, Part):
            yield item.payload
        elif isinstance(item, (list, tuple)):
            # Defensive flattening: the upstream sample accidentally nests a
            # list in one multimodal call. Flattening prevents serialization of
            # Python list repr as text, while the app also fixes that call site.
            yield from _iter_openai_parts(item)
        elif isinstance(item, str):
            yield {"type": "text", "text": item}
        else:
            yield {"type": "text", "text": str(item)}


def to_openai_content(contents: Union[str, list[Any], tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Convert Gemini-style ``contents`` into OpenAI message content parts."""

    if isinstance(contents, str):
        return [{"type": "text", "text": contents}]
    return list(_iter_openai_parts(contents))


def compute_max_completion_tokens(
    max_answer_tokens: Optional[int],
    thinking_budget: Optional[int],
) -> Optional[int]:
    """Translate separate answer/thinking budgets to Qwen's total output cap.

    ``max_completion_tokens`` includes both reasoning and the final answer. The
    migrated UI keeps Gemini's answer-token control, so manual thinking must add
    the thinking allowance (plus a small server-accounting margin) rather than
    treating the answer limit as the total limit.
    """

    if max_answer_tokens is None:
        return None
    if max_answer_tokens < 1:
        raise ValueError("max_answer_tokens must be greater than zero")
    if thinking_budget is not None and thinking_budget > 0:
        return (
            max_answer_tokens
            + thinking_budget
            + THINKING_TOKEN_SAFETY_MARGIN
        )
    return max_answer_tokens


def _message_text(content: Any) -> Optional[str]:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, Mapping) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
        return "".join(text_parts) or str(content)
    return str(content)


class _Models:
    """Expose a Gemini-like ``generate_content`` method over an OpenAI client."""

    def __init__(self, openai_client: Any) -> None:
        self._client = openai_client

    def generate_content(
        self,
        model: str,
        contents: Union[str, list[Any], tuple[Any, ...]],
        config: Optional[GenerateContentConfig] = None,
    ) -> _Response:
        request: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "user", "content": to_openai_content(contents)}
            ],
        }
        extra_body: dict[str, Any] = {}

        if config is not None:
            if config.temperature is not None:
                request["temperature"] = max(
                    0.0, min(config.temperature, MAX_QWEN_TEMPERATURE)
                )
            thinking = config.thinking_config
            thinking_budget = (
                thinking.thinking_budget
                if thinking is not None
                else None
            )

            if config.max_output_tokens is not None:
                # The UI value represents desired final-answer tokens. Qwen's
                # max_completion_tokens covers reasoning + answer, so a manual
                # thinking budget must be added instead of competing with it.
                request["max_completion_tokens"] = compute_max_completion_tokens(
                    config.max_output_tokens, thinking_budget
                )
            if config.top_p is not None:
                if not 0.0 < config.top_p <= 1.0:
                    raise ValueError("top_p must satisfy 0.0 < top_p <= 1.0")
                request["top_p"] = config.top_p
            if thinking_budget is not None:
                if thinking_budget <= 0:
                    extra_body["enable_thinking"] = False
                else:
                    extra_body["enable_thinking"] = True
                    extra_body["thinking_budget"] = thinking_budget

        if extra_body:
            request["extra_body"] = extra_body

        completion = self._client.chat.completions.create(**request)
        return _Response(
            text=_message_text(completion.choices[0].message.content)
        )


class QwenClient:
    """Gemini-like client backed by Model Studio's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY is required")
        if not base_url:
            raise ValueError("A Model Studio base URL is required")

        # Lazy import keeps payload/unit tests runnable without installing the
        # full Streamlit application dependency set first.
        from openai import OpenAI

        self.models = _Models(
            OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        )
