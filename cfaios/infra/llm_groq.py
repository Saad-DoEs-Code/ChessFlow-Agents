"""Groq client wrapper. Fast open-weight text generation for generative/reasoning
agents (7,8,11,13,18,...). All generation obeys P10: callers retrieve+verify BEFORE
calling generate(); this wrapper never sources chess facts itself. Model string is
config-driven."""
from __future__ import annotations

from config.settings import settings


class GroqClient:
    def __init__(self, model: str | None = None):
        self.model = model or settings.groq_model
        self._client = None  # lazily initialised

    def connect(self) -> None:
        if not settings.groq_api_key or settings.groq_api_key in ("...", ""):
            raise RuntimeError(
                "CFAIOS_GROQ_API_KEY is not set. "
                "Add your Groq API key to .env and re-run."
            )
        from groq import Groq
        self._client = Groq(api_key=settings.groq_api_key)

    def _ensure_connected(self) -> None:
        if self._client is None:
            self.connect()

    def generate(self, *, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        """General-purpose text generation with a system prompt.

        `messages` follows the OpenAI-style [{"role": ..., "content": ...}, ...] shape
        Groq's chat-completions API expects.
        """
        self._ensure_connected()
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content.strip()
