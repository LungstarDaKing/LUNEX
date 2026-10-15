"""Builds the provider list from the settings. Only providers that have a key (or run locally) are used."""
from __future__ import annotations

from typing import List

from lunex.ai.providers.anthropic import AnthropicProvider
from lunex.ai.providers.base import AIProvider
from lunex.ai.providers.openai import OpenAIProvider
from lunex.ai.router import ProviderRouter
from lunex.config import Settings

# name -> (base_url, key attribute, model attribute). Anything that copies the OpenAI API works here.
OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "groq_api_key", "groq_model"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini_api_key", "gemini_model"),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter_api_key", "openrouter_model"),
    "openai": (None, "openai_api_key", "openai_model"),
}


def build_providers(s: Settings, http_client=None) -> List[AIProvider]:
    out: List[AIProvider] = []
    for name in [n.strip().lower() for n in s.lunex_providers.split(",") if n.strip()]:
        if name in OPENAI_COMPATIBLE:
            base_url, key_attr, model_attr = OPENAI_COMPATIBLE[name]
            key = getattr(s, key_attr)
            if key:
                out.append(OpenAIProvider({"api_key": key, "model": getattr(s, model_attr), "base_url": base_url,
                                           "timeout": s.lunex_provider_timeout, "http_client": http_client}, name=name))
        elif name == "ollama":
            out.append(OpenAIProvider({"api_key": "ollama", "model": s.ollama_model, "base_url": s.ollama_host.rstrip("/") + "/v1",
                                       "timeout": s.lunex_provider_timeout, "http_client": http_client}, name="ollama"))
        elif name == "anthropic" and s.anthropic_api_key:
            out.append(AnthropicProvider({"api_key": s.anthropic_api_key, "model": s.anthropic_model,
                                          "timeout": s.lunex_provider_timeout}, name="anthropic"))
    return out


def build_router(s: Settings) -> ProviderRouter:
    return ProviderRouter(build_providers(s))
