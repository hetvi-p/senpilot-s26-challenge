import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "local"
    APP_NAME: str = "uarb-matter-mail-agent"
    BASE_URL: str = "http://localhost:8000"
    LOG_LEVEL: str = "INFO"

    REDIS_URL = "redis://red-d6mbhj7afjfc7390jjeg:6379"
    CELERY_BROKER_URL = "redis://red-d6mbhj7afjfc7390jjeg:6379"
    CELERY_RESULT_BACKEND = "redis://red-d6mbhj7afjfc7390jjeg:6379"

    MAILGUN_API_KEY: str = Field(default="", repr=False)
    MAILGUN_DOMAIN: str = ""
    MAILGUN_FROM: str = ""
    MAILGUN_WEBHOOK_SIGNING_KEY: str = Field(default="", repr=False)

    OLLAMA_BASE_URL: str | None = None
    OLLAMA_MODEL: str | None = None

    UARB_BASE_URL: str = "https://uarb.novascotia.ca/fmi/webd/UARB15"

    MAX_DOCS: int = 10
    MAX_ZIP_MB: int = 20

settings = Settings()