"""Google (Gemini) client wrapper. Primary use: multimodal — Agent 1 board-diagram ->
FEN vision, and long-context extraction. Model string is config-driven."""
from __future__ import annotations

from config.settings import settings

_VISION_PROMPT = (
    "This image is a chess board diagram from a chess book. "
    "Extract the position and output it as a FEN piece-placement string "
    "(rank 8 to rank 1, uppercase for White pieces KQRBNP, lowercase for Black kqrbnp, "
    "digits for consecutive empty squares, '/' between ranks). "
    "Output ONLY the FEN piece-placement string — no explanation, no move number, "
    "no other text."
)


class GoogleClient:
    def __init__(self, model: str | None = None):
        self.model = model or settings.google_model
        self._client = None  # lazily initialised

    def connect(self) -> None:
        if not settings.google_api_key or settings.google_api_key in ("...", ""):
            raise RuntimeError(
                "CFAIOS_GOOGLE_API_KEY is not set. "
                "Add your Gemini API key to .env and re-run."
            )
        from google import genai
        self._client = genai.Client(api_key=settings.google_api_key)

    def _ensure_connected(self) -> None:
        if self._client is None:
            self.connect()

    def vision_to_fen(self, image_bytes: bytes, *, mime: str = "image/png") -> str:
        """Send a board-diagram image to Gemini and return the raw FEN string.

        The caller is responsible for validating the returned string with
        python-chess (and ultimately Agent 3). This method makes one API call
        and returns whatever Gemini produces — it does not self-certify.
        """
        self._ensure_connected()
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                types.Part(text=_VISION_PROMPT),
            ],
        )
        return response.text.strip()

    def generate(self, *, system: str, contents: list, max_tokens: int = 1024) -> str:
        """General-purpose text generation with a system prompt."""
        self._ensure_connected()
        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
            contents=contents,
        )
        return response.text.strip()
