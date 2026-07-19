"""Anthropic client wrapper. Used by generative/reasoning agents (7,8,11,13,18,...).
All generation obeys P10: callers retrieve+verify BEFORE calling generate(); this
wrapper never sources chess facts itself. Model string is config-driven."""
from __future__ import annotations
from config.settings import settings


class AnthropicClient:
    def __init__(self, model: str | None = None):
        self.model = model or settings.anthropic_model
        self._client = None

    def connect(self) -> None:
        # TODO(build): from anthropic import Anthropic; self._client = Anthropic(api_key=...)
        raise NotImplementedError("Bind the Anthropic SDK using settings.anthropic_api_key")

    def generate(self, *, system: str, messages: list[dict], max_tokens: int = 1024) -> str:
        raise NotImplementedError
