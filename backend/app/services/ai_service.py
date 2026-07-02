"""Anthropic Claude Haiku client wrapper.

The API key is read server-side from settings and never leaves the backend.
Every call prepends the mandatory Francessca system prompt and clearly
separates untrusted user content from system instructions.
"""
from __future__ import annotations

from dataclasses import dataclass

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

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
