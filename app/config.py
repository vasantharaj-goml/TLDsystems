from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "TLD Regulatory Monitoring Crawler Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Path settings
    CONFIG_PATH: Path = BASE_DIR / "config" / "source_repository.json"
    STORAGE_DIR: Path = BASE_DIR / "storage" / "extracted_content"
    DISCOVERY_STORAGE_DIR: Path = BASE_DIR / "storage" / "discovered_candidates"
    APPROVED_STORAGE_DIR: Path = BASE_DIR / "storage" / "approved_sources"
    
    # Grok / xAI LLM Settings
    GROK_API_KEY: str = ""
    GROK_MODEL: str = "grok-beta"
    GROK_API_BASE: str = "https://api.x.ai/v1"
    GROK_REQUEST_TIMEOUT: int = 30
    
    # CORS settings
    ALLOWED_ORIGINS: Union[List[str], str] = ["*"]

    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )


settings = Settings()