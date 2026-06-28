"""Application configuration via environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    uarb_base_url: str = "https://uarb.novascotia.ca/fmi/webd/UARB15"
    max_downloads: int = 10
    download_dir: Path = Path("./downloads")
    output_dir: Path = Path("./output")

    headless: bool = True
    page_load_timeout_ms: int = 60_000
    action_timeout_ms: int = 30_000

    log_level: str = "INFO"

    # LLM
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Gmail
    gmail_client_id: str | None = None
    gmail_client_secret: str | None = None
    gmail_refresh_token: str | None = None
    gmail_sender_address: str | None = None
    gmail_poll_label: str = "INBOX"
    poll_interval_sec: int = 45


settings = Settings()
