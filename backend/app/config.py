from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Dev default: sqlite file (user requested sqlite3 as of now). Override with postgresql+asyncpg:// for prod.
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./aicouncil.db")
    DATABASE_URL_SYNC: str = Field(default="sqlite:///./aicouncil.db")
    LMARENA_TOKEN: str = Field(..., min_length=1)
    LMARENA_BRIDGE_URL: str = Field(default="http://lmarenabridge:8001")
    FRONTEND_ORIGIN: str = Field(default="http://localhost:3000")
    SECRET_KEY: str = Field(default="change_me_32_chars_min________________________________", min_length=32)
    ADMIN_PASSWORD: str = Field(default="change_me")
    MAX_MODELS_PER_QUERY: int = Field(default=8, ge=2, le=16)
    REQUEST_TIMEOUT: int = Field(default=120, ge=10, le=300)
    LOG_LEVEL: str = Field(default="INFO")
    REDIS_URL: str | None = Field(default=None)
    BACKEND_PORT: int = Field(default=8000)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
