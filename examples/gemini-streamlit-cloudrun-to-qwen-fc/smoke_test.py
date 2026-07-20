#!/usr/bin/env python3
"""Live smoke tests for Model Studio text, image, and video requests."""

from __future__ import annotations

import argparse
import os
import sys

from cloudport_compat import GenerateContentConfig, Part, QwenClient, resolve_base_url

DEFAULT_IMAGE_URL = (
    "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/"
    "zh-CN/20241108/xzsgiz/football1.jpg"
)
DEFAULT_VIDEO_URL = (
    "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/"
    "zh-CN/20241115/cqqkru/1.mp4"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("text", "image", "video", "all"), default="all")
    parser.add_argument("--text-model", default="qwen3.6-flash")
    parser.add_argument("--vision-model", default="qwen3.7-plus")
    parser.add_argument("--image-url", default=DEFAULT_IMAGE_URL)
    parser.add_argument("--video-url", default=DEFAULT_VIDEO_URL)
    return parser.parse_args()


def require_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise SystemExit("DASHSCOPE_API_KEY is not set")
    return key


def run_case(name: str, call) -> None:
    print(f"\n=== {name} ===")
    response = call()
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"{name}: empty response")
    print(text[:1500])
    print(f"[PASS] {name}: {len(text)} characters")


def main() -> int:
    args = parse_args()
    client = QwenClient(
        api_key=require_api_key(),
        base_url=resolve_base_url(),
        timeout=float(os.environ.get("QWEN_TIMEOUT_SECONDS", "180")),
    )
    config = GenerateContentConfig(temperature=0.2, max_output_tokens=512)

    try:
        if args.mode in ("text", "all"):
            run_case(
                "text",
                lambda: client.models.generate_content(
                    model=args.text_model,
                    contents="Reply with exactly: CLOUDPORT_TEXT_OK",
                    config=config,
                ),
            )

        if args.mode in ("image", "all"):
            run_case(
                "image",
                lambda: client.models.generate_content(
                    model=args.vision_model,
                    contents=[
                        Part.from_uri(args.image_url, "image/jpeg"),
                        "Describe this image in one concise sentence.",
                    ],
                    config=config,
                ),
            )

        if args.mode in ("video", "all"):
            run_case(
                "video",
                lambda: client.models.generate_content(
                    model=args.vision_model,
                    contents=[
                        Part.from_uri(args.video_url, "video/mp4"),
                        "Summarize this video in one concise sentence.",
                    ],
                    config=config,
                ),
            )
    except Exception as exc:  # smoke test should expose SDK/API error details
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
