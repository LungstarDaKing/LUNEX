"""Tries the configured providers in order; if one fails or is rate-limited, the next one answers.

A provider that just failed is skipped for a short while, so people are not made to wait for a
broken or exhausted provider on every message.
"""
from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from lunex.ai.providers.base import AIProvider, Message, ProviderError

log = logging.getLogger("lunex.router")


class AllProvidersFailed(Exception):
    """Every provider failed. Message is safe to show to users."""


class ProviderRouter:
    def __init__(self, providers: List[AIProvider], cooldown: float = 60.0):
        self.providers = providers
        self.cooldown = cooldown
        self._until: Dict[str, float] = {}

    @property
    def available(self) -> bool:
        return bool(self.providers)

    def _order(self) -> List[AIProvider]:
        now = time.monotonic()
        ready = [p for p in self.providers if self._until.get(p.provider_name, 0) <= now]
        return ready or list(self.providers)       # if all are cooling down, try them anyway

    def _fail(self, p: AIProvider, e: Exception) -> None:
        log.warning("provider %s failed: %s", p.provider_name, e)
        self._until[p.provider_name] = time.monotonic() + (self.cooldown if getattr(e, "rate_limited", False) else self.cooldown / 3)

    async def chat(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> str:
        if not self.providers:
            raise AllProvidersFailed("LUNEX is not set up with an AI provider yet.")
        for p in self._order():
            try:
                text = await p.chat(messages, options)
                if text.strip():
                    return text
            except ProviderError as e:
                self._fail(p, e)
        raise AllProvidersFailed("LUNEX is busy right now. Please try again in a minute.")

    async def chat_stream(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        """Falls back only if a provider fails before it has produced any text."""
        if not self.providers:
            raise AllProvidersFailed("LUNEX is not set up with an AI provider yet.")
        for p in self._order():
            started = False
            try:
                async for piece in p.chat_stream(messages, options):
                    started = True
                    yield piece
                if started:
                    return
            except ProviderError as e:
                self._fail(p, e)
                if started:                       # cut off half-way: do not mix two providers' text
                    raise AllProvidersFailed("The answer was interrupted. Please ask again.") from e
        raise AllProvidersFailed("LUNEX is busy right now. Please try again in a minute.")
