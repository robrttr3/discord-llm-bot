"""Small async provider adapter. No automatic retries or model substitution."""
import asyncio
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from urllib.parse import quote

import httpx


class ProviderError(Exception):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(kind)  # Never include response bodies, URLs, or credentials.


class AIProvider:
    def __init__(self, settings, key: str, client=None, clock=time.monotonic,
                 day=None):
        self.settings = settings
        self.key = key
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            follow_redirects=False,
        )
        self.clock = clock
        self.day = day or (lambda: datetime.now(timezone.utc).date())
        self.blocked_until = 0.0
        self.block_reason = "outage"
        self.requests_today = 0
        self.current_day = self.day()
        self.lock = asyncio.Lock()

    async def close(self):
        await self.client.aclose()

    def _pause(self, kind, seconds):
        self.block_reason = kind
        self.blocked_until = self.clock() + seconds
        logging.getLogger("orion").warning("AI requests paused: %s. See README troubleshooting.", kind)

    def _check_available(self):
        if self.current_day != self.day():
            self.current_day = self.day()
            self.requests_today = 0
        if self.clock() < self.blocked_until:
            raise ProviderError(self.block_reason)
        if self.requests_today >= self.settings.daily_request_limit:
            raise ProviderError("quota")

    @staticmethod
    def _retry_seconds(response):
        header = response.headers.get("retry-after", "")
        try:
            seconds = float(header)
        except ValueError:
            try:
                seconds = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                seconds = 3600
        # Conservative backoff, even if a service returns a zero or negative delay.
        return max(60, min(seconds, 86400))

    @staticmethod
    def _gemini_bad_request(response):
        """Classify known error signals; never log Google's free-form response."""
        try:
            error = response.json().get("error", {})
            details = error.get("details", [])
            reasons = {item.get("reason") for item in details if isinstance(item, dict)
                       and isinstance(item.get("reason"), str)}
            message = error.get("message", "")
            message = message.casefold() if isinstance(message, str) else ""
            status = error.get("status", "")
        except (ValueError, TypeError, AttributeError):
            reasons, message, status = set(), "", ""
        if "API_KEY_INVALID" in reasons or "api key not valid" in message or "api key expired" in message:
            return "auth", "Google rejected the API key. Check ORION_AI_KEY privately and restart after correcting it."
        if "user location is not supported" in message:
            return "configuration", "Google reports this location is unsupported. Check Gemini API regional eligibility."
        if any(field in message for field in ("thinkinglevel", "thinking_level", "thinkingconfig", "thinking_config")):
            return "configuration", "Google rejected a thinking option. Use the updated Orion adapter, which omits guessed thinking settings."
        if any(field in message for field in ("maxoutputtokens", "max_output_tokens")):
            return "configuration", "Google rejected the output token setting. Check max_output_tokens against this model's documented limits."
        if status == "FAILED_PRECONDITION":
            return "configuration", "Google reports an unmet account prerequisite. Check project, region and free-tier eligibility in AI Studio; do not enable billing just to retry."
        return "configuration", "Google rejected the request (HTTP 400). The status alone does not identify the cause; inspect the detailed error in AI Studio."

    async def generate(self, system: str, conversation: str) -> str:
        if self.lock.locked():
            raise ProviderError("busy")
        async with self.lock:
            self._check_available()
            s = self.settings
            if s.provider == "gemini":
                url = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(s.model, safe="-._") + ":generateContent"
                headers = {"x-goog-api-key": self.key}
                generation = {"maxOutputTokens": s.max_output_tokens}
                # Thinking options differ between models. Use the model's defaults
                # rather than infer supported values from its name prefix.
                body = {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": conversation}]}],
                    "generationConfig": generation,
                    "safetySettings": [
                        {"category": category, "threshold": "BLOCK_LOW_AND_ABOVE"}
                        for category in ("HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_HARASSMENT")
                    ],
                }
            elif s.provider == "openai":
                url = s.base_url.rstrip("/") + "/chat/completions"
                headers = {"Authorization": "Bearer " + self.key}
                body = {
                    "model": s.model,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": conversation}],
                    "max_tokens": s.max_output_tokens,
                }
            else:
                url = s.base_url.rstrip("/") + "/api/chat"
                headers = {}
                body = {
                    "model": s.model, "stream": False,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": conversation}],
                    "options": {"num_predict": s.max_output_tokens},
                }
            self.requests_today += 1
            try:
                async with asyncio.timeout(s.request_timeout_seconds):
                    response = await self.client.post(url, headers=headers, json=body)
            except (TimeoutError, httpx.TimeoutException, httpx.TransportError):
                self._pause("outage", 60)
                raise ProviderError("outage") from None
            status = response.status_code
            if status == 429:
                self._pause("quota", self._retry_seconds(response))
                raise ProviderError("quota")
            if status in (401, 403):
                self._pause("auth", 3600)
                raise ProviderError("auth")
            if status == 400 and s.provider == "gemini":
                kind, hint = self._gemini_bad_request(response)
                logging.getLogger("orion").warning("%s", hint)
                self._pause(kind, 3600)
                raise ProviderError(kind)
            if status in (400, 404, 422):
                self._pause("configuration", 3600)
                raise ProviderError("configuration")
            if not 200 <= status < 300:
                self._pause("outage", 60)
                raise ProviderError("outage")
            try:
                data = response.json()
                if s.provider == "gemini":
                    candidates = data.get("candidates", [])
                    if data.get("promptFeedback", {}).get("blockReason"):
                        raise ProviderError("safety")
                    candidate = candidates[0] if candidates else {}
                    if candidate.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST"):
                        raise ProviderError("safety")
                    result = "".join(
                        part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                        if not part.get("thought")
                    )
                elif s.provider == "openai":
                    result = data["choices"][0]["message"]["content"]
                else:
                    result = data["message"]["content"]
                if not isinstance(result, str) or not result.strip():
                    raise ValueError
                return result
            except (ValueError, KeyError, TypeError, IndexError, AttributeError):
                self._pause("empty", 60)
                raise ProviderError("empty") from None
