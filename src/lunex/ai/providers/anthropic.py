"""Anthropic (Claude). Note: Anthropic has no free API tier, so this is optional in LUNEX."""
from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic

from lunex.ai.providers.base import AIProvider, Message, ProviderError
from lunex.ai.providers.capabilities import ProviderCapabilities


def split_messages(messages: List[Message]) -> tuple[str, List[Message]]:
    """Anthropic wants the system text separate, and user/assistant turns that strictly alternate."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns: List[Message] = []
    for m in messages:
        if m["role"] not in ("user", "assistant"):
            continue
        if turns and turns[-1]["role"] == m["role"]:
            turns[-1] = {"role": m["role"], "content": turns[-1]["content"] + "\n\n" + m["content"]}
        else:
            turns.append({"role": m["role"], "content": m["content"]})
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return system, turns


class AnthropicProvider(AIProvider):
    def __init__(self, config: Dict[str, Any], name: str = "anthropic"):
        super().__init__(name, config)
        self.client = anthropic.AsyncAnthropic(api_key=config.get("api_key"), timeout=config.get("timeout", 40.0), max_retries=0)

    def _detect_capabilities(self) -> ProviderCapabilities:
        caps = ProviderCapabilities.TEXT | ProviderCapabilities.STREAMING
        if self.config.get("vision_capable"):
            caps |= ProviderCapabilities.VISION
        if self.config.get("function_calling_capable"):
            caps |= ProviderCapabilities.FUNCTION_CALLING
        return caps

    def _kwargs(self, messages: List[Message], options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        system, turns = split_messages(messages)
        o = dict(options or {})
        kw: Dict[str, Any] = {"model": self.config["model"], "max_tokens": o.pop("max_tokens", 700),
                              "temperature": o.pop("temperature", 0.6), "messages": turns, **o}
        if system:
            kw["system"] = system
        return kw

    def _wrap(self, e: Exception) -> ProviderError:
        return ProviderError(self.provider_name, type(e).__name__, rate_limited=isinstance(e, anthropic.RateLimitError))

    async def chat(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> str:
        try:
            r = await self.client.messages.create(**self._kwargs(messages, options))
        except anthropic.AnthropicError as e:
            raise self._wrap(e) from e
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

    async def chat_stream(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        try:
            async with self.client.messages.stream(**self._kwargs(messages, options)) as s:
                async for text in s.text_stream:
                    yield text
        except anthropic.AnthropicError as e:
            raise self._wrap(e) from e
