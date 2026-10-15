"""OpenAI and every service that copies its API: Groq, Google Gemini, OpenRouter, Mistral, Ollama...

Set `base_url` to point at one of those. Failures are turned into ProviderError so the router can
fall back to the next provider.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from lunex.ai.providers.base import AIProvider, Message, ProviderError
from lunex.ai.providers.capabilities import ProviderCapabilities


class OpenAIProvider(AIProvider):
    def __init__(self, config: Dict[str, Any], name: str = "openai"):
        super().__init__(name, config)
        self.client = AsyncOpenAI(
            api_key=config.get("api_key") or "not-needed",   # local servers such as Ollama need no key
            base_url=config.get("base_url"),
            timeout=config.get("timeout", 40.0),
            max_retries=0,                                    # LUNEX does its own fallback
            http_client=config.get("http_client"),
        )

    def _detect_capabilities(self) -> ProviderCapabilities:
        caps = ProviderCapabilities.TEXT | ProviderCapabilities.STREAMING
        if self.config.get("vision_capable"):
            caps |= ProviderCapabilities.VISION
        if self.config.get("function_calling_capable"):
            caps |= ProviderCapabilities.FUNCTION_CALLING
        return caps

    def _kwargs(self, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        o = dict(options or {})
        return {"max_tokens": o.pop("max_tokens", 700), "temperature": o.pop("temperature", 0.6), **o}

    def _wrap(self, e: Exception) -> ProviderError:
        limited = isinstance(e, openai.RateLimitError) or getattr(e, "status_code", None) == 429
        return ProviderError(self.provider_name, f"{type(e).__name__}", rate_limited=limited)

    async def chat(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> str:
        try:
            r = await self.client.chat.completions.create(model=self.config["model"], messages=messages, **self._kwargs(options))
        except openai.OpenAIError as e:
            raise self._wrap(e) from e
        return (r.choices[0].message.content or "") if r.choices else ""

    async def chat_stream(self, messages: List[Message], options: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.config["model"], messages=messages, stream=True, **self._kwargs(options))
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.OpenAIError as e:
            raise self._wrap(e) from e
