from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# FAIL-SAFE .ENV LOADING
# This ensures that no matter where the server is started from,
# it will find the .env file in the project root.
project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback to current directory
    load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "CLARIO"
    DATABASE_URL: str = Field(default="sqlite:///./clario.db", repr=False)
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI Provider Settings
    AI_PROVIDER: str = "mock"
    AI_MODEL: Optional[str] = None

    # Provider API Keys (optional in environment)
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_ignore_empty=True,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

settings = Settings()
