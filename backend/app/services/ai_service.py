"""Model clients.

Two interchangeable backends, both returning an `AIResult`:

- `AIService` — the hosted Anthropic API. The key is read server-side from
  settings and never leaves the backend.
- `LocalAIService` — any OpenAI-compatible server on localhost. This is what
  the offline desktop build talks to (a bundled llama.cpp serving a small
  instruct model), so nothing leaves the user's machine at all.

`build_ai_service()` picks between them from `AI_PROVIDER`. Every call
prepends the mandatory Francessca system prompt and keeps untrusted user
content in user turns, separate from system instructions — identical on
both backends.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from anthropic import Anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.logging import get_logger, log_event

log = get_logger("francessca.ai")


@dataclass
class AIResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class AIService:
    """Thin, testable wrapper around the Anthropic Messages API."""

    # Roughly how much prompt this backend can be given. Hosted Claude has
    # room to spare; see LocalAIService for why the local one does not.
    context_char_budget = 400_000

    def __init__(self, client: Anthropic | None = None) -> None:
        self._client = client
        self.model = settings.anthropic_model

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> AIResult:
        """Send a completion request.

        `messages` is the conversation history as a list of
        {"role": "user"|"assistant", "content": str}. The system prompt is
        passed via the dedicated `system` parameter — it is NEVER mixed into
        the user turns, which keeps system guardrails isolated from user input.
        """
        resp = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            max_tokens=max_tokens,
            messages=messages,
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        result = AIResult(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=self.model,
        )
        log_event(
            log, "ai_request", model=self.model,
            input=result.input_tokens, output=result.output_tokens,
        )
        return result


# Reasoning models (Qwen3, DeepSeek-R1 and friends) put their scratch work in
# <think> blocks and only then answer. Nothing downstream should ever see it:
# it would be shown to the user, stored in the transcript, and fed back as
# context on the next turn.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove <think> blocks, including one left unterminated by truncation."""
    text = _THINK_BLOCK.sub("", text)
    text = _UNCLOSED_THINK.sub("", text)
    return text.strip()


class LocalAIService:
    """OpenAI-compatible client for a locally served model.

    Deliberately duck-typed against `AIService` rather than sharing a base
    class: the two speak different wire protocols and there is exactly one
    method in common.
    """

    # Ollama serves 4096 tokens of context by default, and llama.cpp is
    # started with 8192 here. Everything sent -- system prompt, history,
    # document text -- eats into the same window, and whatever is left is all
    # the room the model has to answer in. Overrun it and replies come back
    # two tokens long. ~6000 characters is roughly 1500 tokens, which leaves
    # a comfortable margin even on the smaller default.
    context_char_budget = 6_000

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.local_ai_base_url).rstrip("/")
        self.model = model or settings.local_ai_model

    def health(self) -> bool:
        """True when the local server is up — used by the desktop launcher."""
        try:
            resp = httpx.get(f"{self.base_url}/models", timeout=3.0)
            return resp.status_code < 500
        except Exception:  # noqa: BLE001 - any failure means "not ready"
            return False

    # Retry a refused connection (the server is still loading the model), but
    # never a timeout: a local model that needed longer than the timeout will
    # need just as long again, and the user waits twice for the same failure.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=4),
        retry=retry_if_exception_type(httpx.ConnectError),
        reraise=True,
    )
    def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> AIResult:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": max_tokens,
            # Low but not zero: the guardrails and the question protocol need
            # to be followed closely, and small models drift when hot.
            "temperature": 0.3,
            "stream": False,
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=settings.local_ai_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        choices = data.get("choices") or []
        if choices:
            text = (choices[0].get("message") or {}).get("content") or ""
        text = strip_reasoning(text)
        usage = data.get("usage") or {}
        result = AIResult(
            text=text,
            # llama.cpp reports these; anything that does not simply logs 0.
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            model=data.get("model") or self.model,
        )
        log_event(
            log, "ai_request", model=result.model, provider="local",
            input=result.input_tokens, output=result.output_tokens,
        )
        return result


def build_ai_service() -> "AIService | LocalAIService":
    """The model client this deployment should use.

    Services take an `ai=` argument for tests; this is only the default.
    """
    return LocalAIService() if settings.is_local_ai else AIService()
