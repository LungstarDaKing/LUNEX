"""All settings come from environment variables (or a local .env file). See .env.example."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- general ---
    lunex_env: str = "development"            # development | production
    lunex_app_name: str = "LSDKChat"
    lunex_app_url: str = "https://lungstardaking.github.io/LSDKChat/"
    lunex_support_contact: str = ""           # shown when LUNEX cannot answer an app question

    # --- who may talk to LUNEX ---
    lunex_auth: str = "supabase"              # supabase | off   ("off" only works in development)
    supabase_url: str = ""                    # https://xxxx.supabase.co
    supabase_anon_key: str = ""               # the public/publishable key (same one the app uses)
    lunex_api_token: str = ""                 # optional secret for server-to-server calls
    lunex_allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    # --- AI providers: tried in this order, the next one is used when one fails or is rate-limited ---
    lunex_providers: str = "groq,gemini,openrouter"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- protection for free quotas ---
    lunex_user_per_minute: int = 6
    lunex_user_per_day: int = 80
    lunex_global_per_day: int = 1500
    lunex_max_message_chars: int = 2000
    lunex_max_history: int = 12
    lunex_max_output_tokens: int = 700
    lunex_provider_timeout: float = 40.0

    # --- web research ---
    lunex_research_pages: int = 3
    lunex_knowledge_dir: str = ""             # optional extra folder of .md files for app help

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.lunex_allowed_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.lunex_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
