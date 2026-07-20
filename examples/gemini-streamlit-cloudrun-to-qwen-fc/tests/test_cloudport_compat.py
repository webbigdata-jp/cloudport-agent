import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cloudport_compat import (  # noqa: E402
    DEFAULT_BASE_URL,
    GenerateContentConfig,
    Part,
    ThinkingConfig,
    THINKING_TOKEN_SAFETY_MARGIN,
    _Models,
    compute_max_completion_tokens,
    resolve_base_url,
    to_openai_content,
)


class FakeCompletions:
    def __init__(self, content="ok"):
        self.content = content
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        message = SimpleNamespace(content=self.content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class FakeClient:
    def __init__(self, content="ok"):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


class PartConversionTests(unittest.TestCase):
    def test_image_part(self):
        part = Part.from_uri("https://example.com/a.jpg", "image/jpeg")
        self.assertEqual(
            part.payload,
            {"type": "image_url", "image_url": {"url": "https://example.com/a.jpg"}},
        )

    def test_video_part(self):
        part = Part.from_uri("https://example.com/a.mp4", "video/mp4")
        self.assertEqual(part.payload["type"], "video_url")
        self.assertEqual(part.payload["video_url"]["url"], "https://example.com/a.mp4")
        self.assertEqual(part.payload["fps"], 2)

    def test_unsupported_mime_rejected(self):
        with self.assertRaises(ValueError):
            Part.from_uri("https://example.com/a.pdf", "application/pdf")

    def test_nested_content_is_flattened(self):
        content = to_openai_content(
            ["before", [Part.from_uri("https://example.com/a.jpg", "image/jpeg"), "after"]]
        )
        self.assertEqual([item["type"] for item in content], ["text", "image_url", "text"])


class RequestMappingTests(unittest.TestCase):
    def test_sampling_and_token_names_are_mapped(self):
        client = FakeClient()
        models = _Models(client)
        response = models.generate_content(
            model="qwen3.6-flash",
            contents="hello",
            config=GenerateContentConfig(
                temperature=2.0,
                max_output_tokens=321,
                top_p=0.8,
            ),
        )
        request = client.chat.completions.last_request
        self.assertEqual(response.text, "ok")
        self.assertEqual(request["temperature"], 1.99)
        self.assertEqual(request["max_completion_tokens"], 321)
        self.assertEqual(request["top_p"], 0.8)
        self.assertNotIn("extra_body", request)

    def test_invalid_top_p_is_rejected_before_api_call(self):
        for invalid_top_p in (0.0, -0.1, 1.01):
            with self.subTest(top_p=invalid_top_p):
                client = FakeClient()
                with self.assertRaisesRegex(
                    ValueError, r"top_p must satisfy 0\.0 < top_p <= 1\.0"
                ):
                    _Models(client).generate_content(
                        model="qwen3.6-flash",
                        contents="hello",
                        config=GenerateContentConfig(top_p=invalid_top_p),
                    )
                self.assertIsNone(client.chat.completions.last_request)

    def test_thinking_off(self):
        client = FakeClient()
        _Models(client).generate_content(
            model="qwen3.7-plus",
            contents="hello",
            config=GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_budget=0)
            ),
        )
        request = client.chat.completions.last_request
        self.assertEqual(request["extra_body"], {"enable_thinking": False})

    def test_manual_thinking_budget(self):
        client = FakeClient()
        _Models(client).generate_content(
            model="qwen3.7-plus",
            contents="hello",
            config=GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_budget=4096)
            ),
        )
        request = client.chat.completions.last_request
        self.assertEqual(
            request["extra_body"],
            {"enable_thinking": True, "thinking_budget": 4096},
        )

    def test_manual_thinking_expands_total_output_limit(self):
        client = FakeClient()
        _Models(client).generate_content(
            model="qwen3.7-plus",
            contents="hello",
            config=GenerateContentConfig(
                max_output_tokens=2048,
                thinking_config=ThinkingConfig(thinking_budget=4096),
            ),
        )
        request = client.chat.completions.last_request
        self.assertEqual(
            request["max_completion_tokens"],
            2048 + 4096 + THINKING_TOKEN_SAFETY_MARGIN,
        )
        self.assertGreater(
            request["max_completion_tokens"],
            request["extra_body"]["thinking_budget"],
        )

    def test_compute_total_without_manual_thinking(self):
        self.assertEqual(compute_max_completion_tokens(2048, None), 2048)
        self.assertEqual(compute_max_completion_tokens(2048, 0), 2048)

    def test_multimodal_message_shape(self):
        client = FakeClient(content=[{"type": "text", "text": "vision ok"}])
        response = _Models(client).generate_content(
            model="qwen3.7-plus",
            contents=[
                Part.from_uri("https://example.com/a.jpg", "image/jpeg"),
                "describe",
            ],
        )
        request = client.chat.completions.last_request
        self.assertEqual(response.text, "vision ok")
        self.assertEqual(
            [p["type"] for p in request["messages"][0]["content"]],
            ["image_url", "text"],
        )


class EndpointTests(unittest.TestCase):
    def test_explicit_base_url_wins_and_trailing_slash_removed(self):
        env = {
            "DASHSCOPE_BASE_URL": "https://example.test/compatible-mode/v1/",
            "DASHSCOPE_REGION": "tokyo",
            "DASHSCOPE_WORKSPACE_ID": "ws",
        }
        self.assertEqual(
            resolve_base_url(env), "https://example.test/compatible-mode/v1"
        )

    def test_tokyo_workspace_url(self):
        env = {"DASHSCOPE_REGION": "tokyo", "DASHSCOPE_WORKSPACE_ID": "ws123"}
        self.assertEqual(
            resolve_base_url(env),
            "https://ws123.ap-northeast-1.maas.aliyuncs.com/compatible-mode/v1",
        )

    def test_virginia_fixed_url(self):
        self.assertEqual(
            resolve_base_url({"DASHSCOPE_REGION": "virginia"}),
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
        )

    def test_legacy_fallback(self):
        self.assertEqual(resolve_base_url({}), DEFAULT_BASE_URL)


if __name__ == "__main__":
    unittest.main()
