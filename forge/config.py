"""Provider and model configuration for Agent Forge.

Settings resolve from (highest priority first):
  1. explicit CLI flags
  2. environment variables
  3. documented defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class Config:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout_seconds: int = 120

    @staticmethod
    def from_env(
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> "Config":
        return Config(
            base_url=(
                base_url
                or os.environ.get("FORGE_BASE_URL")
                or DEFAULT_BASE_URL
            ).rstrip("/"),
            api_key=api_key or os.environ.get("FORGE_API_KEY") or "",
            model=model or os.environ.get("FORGE_MODEL") or DEFAULT_MODEL,
            temperature=float(os.environ.get("FORGE_TEMPERATURE", "0.2")),
            max_tokens=int(os.environ.get("FORGE_MAX_TOKENS", "2048")),
            timeout_seconds=int(os.environ.get("FORGE_TIMEOUT", "120")),
        )

    def describe(self) -> str:
        """Human-readable summary without leaking the key."""
        key_state = "set" if self.api_key else "missing"
        return f"{self.model} @ {self.base_url} (api key: {key_state})"
