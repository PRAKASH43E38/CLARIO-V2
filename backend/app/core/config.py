from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "CLARIO"
    DATABASE_URL: str = "sqlite:///./clario.db"

    # AI Provider Settings
    AI_PROVIDER: str = "mock"  # "mock", "gemini", "openrouter", "mistral"
    AI_MODEL: Optional[str] = "gemini-1.5-flash"
    AI_FALLBACK_PROVIDER: Optional[str] = "mock"

    # Provider API Keys (optional in environment)
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
