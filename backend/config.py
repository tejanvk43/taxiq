import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel


_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _get_env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None else v


def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


class Settings(BaseModel):
    ANTHROPIC_API_KEY: str  # kept for backward compat
    GOOGLE_API_KEY: str      # primary — free Gemini
    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    DATABASE_URL: str
    REDIS_URL: str
    MOCK_GSTN: bool
    GSTN_API_KEY: str
    DEBUG: bool
    APP_ENV: str

    @property
    def demo_mode(self) -> bool:
        return not bool(self.GOOGLE_API_KEY) and not bool(self.ANTHROPIC_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        ANTHROPIC_API_KEY=_get_env("ANTHROPIC_API_KEY", ""),
        GOOGLE_API_KEY=_get_env("GOOGLE_API_KEY", ""),
        NEO4J_URI=_get_env("NEO4J_URI", "neo4j+s://2183d7a4.databases.neo4j.io"),
        NEO4J_USERNAME=_get_env("NEO4J_USERNAME", "2183d7a4"),
        NEO4J_PASSWORD=_get_env("NEO4J_PASSWORD", "taxiq123"),
        DATABASE_URL=_get_env("DATABASE_URL", "postgresql://taxiq_user:taxiq_pass@localhost:5432/taxiq"),
        REDIS_URL=_get_env("REDIS_URL", "redis://localhost:6379/0"),
        MOCK_GSTN=_get_bool("MOCK_GSTN", True),
        GSTN_API_KEY=_get_env("GSTN_API_KEY", ""),
        DEBUG=_get_bool("DEBUG", True),
        APP_ENV=_get_env("APP_ENV", "development"),
    )


settings = get_settings()

