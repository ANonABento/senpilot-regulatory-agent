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

    # Gmail (IMAP poll + SMTP send, authenticated with an App Password)
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    mailbox: str = "INBOX"
    poll_interval_sec: int = 45


settings = Settings()
