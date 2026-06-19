from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    max_validation_retries: int = 1
    agent_timeout_s: int = 60
    json_repair_retries: int = 1
    agent_api_retries: int = 1
    agent_retry_backoff_s: float = 1.0

    # Groq — llama-3.3-70b-versatile free-tier limits
    groq_rpm: int = 30
    groq_rpd: int = 1000
    groq_tpm: int = 12000
    groq_tpd: int = 100000

    # Gemini 3 Flash free-tier limits
    gemini_rpm: int = 5
    gemini_rpd: int = 20
    gemini_tpm: int = 250000

    rate_limit_enabled: bool = True
    groq_max_tokens: int = 4096
    gemini_max_tokens: int = 4096

    # Data source: "llm" (current) | "web_search" | "apis" (future — not implemented)
    data_source: str = "llm"

    # Build Phase 2: set false to serialize gather agents and reduce Groq burst load
    gather_parallel: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
