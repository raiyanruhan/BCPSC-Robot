import os
import yaml
from pydantic_settings import BaseSettings
from typing import Dict, Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5/weather"
    
    NEWS_API_KEY: Optional[str] = None
    NEWS_API_URL: str = "https://newsdata.io/api/1/latest"
    
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None  # Default/legacy CSE ID
    GOOGLE_CSE_ID_INTERNATIONAL: Optional[str] = None  # For international web searches
    GOOGLE_CSE_ID_SCHOOL: Optional[str] = None  # For school-related searches
    
    REDIS_URL: str = "redis://localhost:6379/0"
    ADMIN_TOKEN: str
    
    DEFAULT_CACHE_TTL_SECONDS: Dict[str, int] = {
        "weather": 30,
        "news": 60,
        "webSearch": 60,
        "school_info": 3600
    }
    
    CLOUD_REGION: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

def load_config_from_file(file_path: str = "config.md") -> Dict:
    """
    Parses the config.md file which is expected to be in YAML-like format.
    """
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, "r") as f:
        try:
            # The config.md is essentially YAML, so we can use safe_load
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing config.md: {e}")
            return {}

def get_settings() -> Settings:
    # 1. Load from environment (handled by Pydantic BaseSettings defaults/env_file)
    # 2. Load from config.md and override
    
    file_config = load_config_from_file()
    
    # Filter out None values or empty strings from file_config to avoid overwriting defaults with empty
    clean_config = {k: v for k, v in file_config.items() if v is not None}
    
    # We can pass the file config as kwargs to Settings
    # Environment variables should take precedence over file config in a typical 12-factor app,
    # but the prompt says "The service must read keys only from environment variables or the config file".
    # And "expect the service to pick those keys up without manual code changes" (from config.md).
    # So we should probably prioritize config.md if it exists and has values, or merge them.
    # Pydantic Settings priority: arguments > env vars > secrets > config file > defaults.
    # So passing as arguments will override env vars.
    
    return Settings(**clean_config)

settings = get_settings()
