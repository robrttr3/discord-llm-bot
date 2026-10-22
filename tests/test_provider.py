from dataclasses import replace
from datetime import date
import json
import unittest

import httpx

from ai_provider import AIProvider, ProviderError
from config import Settings


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def make_provider(self, handler, settings=None):
        self.now = [100.0]
        self.today = [date(2026, 10, 22)]
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        provider = AIProvider(settings or Settings(), "fake-test-key", client,
                              clock=lambda: self.now[0], day=lambda: self.today[0])
        self.addAsyncCleanup(provider.close)
        return provider

    async def test_gemini_request_and_thought_exclusion(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(request.headers["x-goog-api-key"], "fake-test-key")
            self.assertNotIn("key=", str(request.url))
            self.assertIn("gemini-3.8-flash:generateContent", str(request.url))
            self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "trusted")
            self.assertEqual(body["contents"][0]["role"], "user")
            self.assertEqual(len(body["safetySettings"]), 2)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [
                {"thought": True, "text": "private reasoning"}, {"text": "Hello there."}]}}]})
        provider = self.make_provider(handler)
        self.assertEqual(await provider.generate("trusted", "untrusted"), "Hello there.")
        self.assertEqual(provider.requests_today, 1)

    async def test_openai_compatible(self):
        def handler(request):
            self.assertTrue(str(request.url).endswith("/chat/completions"))
            self.assertEqual(json.loads(request.content)["model"], "openai/gpt-oss-120b")
            return httpx.Response(200, json={"choices": [{"message": {"content": "Hello."}}]})
        provider = self.make_provider(handler, replace(Settings(), provider="openai", model="openai/gpt-oss-120b"))
        self.assertEqual(await provider.generate("s", "u"), "Hello.")

    async def test_gemini_does_not_guess_model_specific_thinking_options(self):
        for model in ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview", "gemini-2.5-pro"):
            with self.subTest(model=model):
                def handler(request):
                    generation = json.loads(request.content)["generationConfig"]
                    self.assertEqual(generation, {"maxOutputTokens": Settings().max_output_tokens})
                    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hello."}]}}]})
                provider = self.make_provider(handler, replace(Settings(), model=model))
                self.assertEqual(await provider.generate("s", "u"), "Hello.")

    async def test_ollama_no_key_transmitted(self):
        def handler(request):
            self.assertNotIn("authorization", request.headers)
            self.assertNotIn("x-goog-api-key", request.headers)
            self.assertTrue(str(request.url).endswith("/api/chat"))
            return httpx.Response(200, json={"message": {"content": "Hello."}})
        provider = self.make_provider(handler, replace(Settings(), provider="ollama", base_url="http://127.0.0.1:11434"))
        self.assertEqual(await provider.generate("s", "u"), "Hello.")

    async def test_rate_limit_circuit_and_retry_after(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429, headers={"Retry-After": "120"}, json={"error": "not logged"})
        provider = self.make_provider(handler)
        for _ in range(3):
            with self.assertRaises(ProviderError) as error:
                await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, "quota")
        self.assertEqual(len(calls), 1)
        self.now[0] += 121
        with self.assertRaises(ProviderError):
            await provider.generate("s", "u")
        self.assertEqual(len(calls), 2)

    async def test_error_statuses_stop_repeated_requests(self):
        for status, expected in ((401, "auth"), (403, "auth"), (404, "configuration"),
                                 (400, "configuration"), (500, "outage"), (302, "outage")):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, text="potentially sensitive response")
            provider = self.make_provider(handler)
            for _ in range(2):
                with self.assertRaises(ProviderError) as error:
                    await provider.generate("s", "u")
                self.assertEqual(str(error.exception), expected)
            self.assertEqual(len(calls), 1)

    async def test_timeout_opens_circuit(self):
        calls = []
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout("not logged", request=request)
        provider = self.make_provider(handler)
        for _ in range(2):
            with self.assertRaises(ProviderError) as error:
                await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, "outage")
        self.assertEqual(len(calls), 1)

    async def test_bad_request_hints_do_not_log_provider_text_or_keys(self):
        cases = [
            ({"status": "INVALID_ARGUMENT", "message": "secret-marker thinkingLevel unsupported"}, "configuration", "thinking option"),
            ({"status": "INVALID_ARGUMENT", "message": "secret-marker", "details": [{"reason": "API_KEY_INVALID"}]}, "auth", "rejected the API key"),
            ({"status": "FAILED_PRECONDITION", "message": "secret-marker"}, "configuration", "account prerequisite"),
            ({"message": "secret-marker maxOutputTokens invalid"}, "configuration", "output token"),
            ({"message": "secret-marker User location is not supported"}, "configuration", "location is unsupported"),
            ({"message": "secret-marker unknown problem"}, "configuration", "status alone"),
        ]
        for body, kind, hint in cases:
            provider = self.make_provider(lambda request: httpx.Response(400, json={"error": body}))
            with self.assertLogs("orion", level="WARNING") as logs:
                with self.assertRaises(ProviderError) as error:
                    await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, kind)
            combined = " ".join(logs.output)
            self.assertIn(hint, combined)
            self.assertNotIn("secret-marker", combined)
            self.assertNotIn("fake-test-key", combined)

    async def test_transport_hints_distinguish_failures_without_leaking_details(self):
        cases = ((httpx.ReadTimeout, "timed out"), (TimeoutError, "timed out"),
                 (httpx.ProxyError, "proxy connection failed"),
                 (httpx.ConnectError, "network connection failed"))
        for exception_type, hint in cases:
            def handler(request):
                raise exception_type("sensitive-exception-marker")
            provider = self.make_provider(handler)
            with self.assertLogs("orion", level="WARNING") as logs:
                with self.assertRaises(ProviderError) as error:
                    await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, "outage")
            combined = " ".join(logs.output)
            self.assertIn(hint, combined)
            self.assertNotIn("sensitive-exception-marker", combined)
            self.assertNotIn("fake-test-key", combined)

    async def test_http_outage_diagnostic_reports_status_without_body(self):
        for status in (302, 500, 502, 503, 504):
            provider = self.make_provider(lambda request: httpx.Response(status, text="sensitive-response-marker"))
            with self.assertLogs("orion", level="WARNING") as logs:
                with self.assertRaises(ProviderError) as error:
                    await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, "outage")
            combined = " ".join(logs.output)
            self.assertIn("HTTP " + str(status), combined)
            self.assertNotIn("sensitive-response-marker", combined)
            self.assertNotIn("fake-test-key", combined)

    async def test_malformed_bad_request_body_has_safe_generic_hint(self):
        for body in ([], {"error": []}, {"error": {"details": None}}):
            response = httpx.Response(400, json=body)
            kind, hint = AIProvider._gemini_bad_request(response)
            self.assertEqual(kind, "configuration")
            self.assertIn("status alone", hint)

    async def test_daily_limit_and_next_day(self):
        def handler(request):
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]})
        provider = self.make_provider(handler, replace(Settings(), daily_request_limit=1))
        await provider.generate("s", "u")
        with self.assertRaises(ProviderError) as error:
            await provider.generate("s", "u")
        self.assertEqual(error.exception.kind, "quota")
        self.today[0] = date(2026, 10, 23)
        self.assertEqual(await provider.generate("s", "u"), "Hi")

    async def test_safety_refusal_does_not_disclose_body(self):
        provider = self.make_provider(lambda request: httpx.Response(200, json={
            "promptFeedback": {"blockReason": "SAFETY"}}))
        with self.assertRaises(ProviderError) as error:
            await provider.generate("s", "u")
        self.assertEqual(str(error.exception), "safety")

    async def test_empty_and_malformed_responses(self):
        for value in ({}, {"candidates": []}, {"candidates": [{"content": {"parts": [{"text": ""}]}}]}, []):
            provider = self.make_provider(lambda request: httpx.Response(200, json=value))
            with self.assertRaises(ProviderError) as error:
                await provider.generate("s", "u")
            self.assertEqual(error.exception.kind, "empty")
