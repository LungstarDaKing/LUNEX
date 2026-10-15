"""Common interface for every AI provider.

Providers speak in *messages* (a list of {"role", "content"} dicts, like every chat API), so LUNEX can
hold a real conversation. The older one-prompt helpers generate()/stream() still work and simply wrap them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from lunex.ai.providers.capabilities import ProviderCapabilities

Message = Dict[str, str]


class CapabilityNotSupported(Exception):
    """Raised when a provider doesn't support a requested capability."""


class ProviderError(Exception):
    """A provider failed (rate limit, outage, bad key...). The router then tries the next provider."""

    def __init__(self, provider: str, message: str, *, rate_limited: bool = False):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.rate_limited = rate_limited


class AIProvider(ABC):
    def __init__(self, provider_name: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.config = config
        self._capabilities = self._detect_capabilities()

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @abstractmethod
    async def chat(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> str:
        """Full reply to a conversation."""

    @abstractmethod
    def chat_stream(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        """Reply as it is written, piece by piece (an async generator)."""

    # --- backwards compatible one-prompt helpers ---
    async def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None,
                       provider_options: Optional[Dict[str, Any]] = None) -> str:
        return await self.chat([{"role": "user", "content": prompt}], {**(options or {}), **(provider_options or {})})

    def stream(self, prompt: str, options: Optional[Dict[str, Any]] = None,
               provider_options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        return self.chat_stream([{"role": "user", "content": prompt}], {**(options or {}), **(provider_options or {})})

    async def embeddings(self, text: str, options: Dict[str, Any]) -> list[float]:
        raise CapabilityNotSupported("Embeddings not supported")

    @abstractmethod
    def _detect_capabilities(self) -> ProviderCapabilities:
        ...
