# backend/config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "VyaparAI API"
    PORT: int = 8000
    DEBUG: bool = True

    # Supabase Settings
    SUPABASE_URL: str = "https://your-supabase-project.supabase.co"
    SUPABASE_KEY: str = "your-supabase-anon-or-service-key"

    # Ollama LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # Storage Settings
    STATIC_DIR: Path = Path(__file__).resolve().parent / "static"
    MEDIA_DIR: Path = Path(__file__).resolve().parent / "static" / "media"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure static and media dirs exist
os.makedirs(settings.STATIC_DIR, exist_ok=True)
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
