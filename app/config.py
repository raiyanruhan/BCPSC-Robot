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

def load_config_from_file(file_path: str = None) -> Dict:
    """
    Parses the config.md file which is expected to be in YAML-like format.
    Looks for config.md in robot-brain directory or current directory.
    """
    if file_path is None:
        # Try to find config.md in robot-brain directory first
        # Get the directory where this file is located
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to robot-brain directory
        robot_brain_dir = os.path.dirname(current_file_dir)
        config_path = os.path.join(robot_brain_dir, "config.md")
        
        # If not found, try current directory
        if not os.path.exists(config_path):
            config_path = "config.md"
    else:
        config_path = file_path
    
    if not os.path.exists(config_path):
        return {}
    
    with open(config_path, "r") as f:
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
    clean_config = {k: v for k, v in file_config.items() if v is not None and k != 'weather' and k != 'news' and k != 'webSearch'}
    
    # Fix DEFAULT_CACHE_TTL_SECONDS structure if it was parsed incorrectly
    if 'DEFAULT_CACHE_TTL_SECONDS' in file_config and isinstance(file_config['DEFAULT_CACHE_TTL_SECONDS'], dict):
        clean_config['DEFAULT_CACHE_TTL_SECONDS'] = file_config['DEFAULT_CACHE_TTL_SECONDS']
    elif 'weather' in file_config or 'news' in file_config or 'webSearch' in file_config:
        # Reconstruct DEFAULT_CACHE_TTL_SECONDS from individual keys
        cache_ttl = {}
        if 'weather' in file_config:
            cache_ttl['weather'] = file_config['weather']
        if 'news' in file_config:
            cache_ttl['news'] = file_config['news']
        if 'webSearch' in file_config:
            cache_ttl['webSearch'] = file_config['webSearch']
        if cache_ttl:
            clean_config['DEFAULT_CACHE_TTL_SECONDS'] = cache_ttl
    
    # We can pass the file config as kwargs to Settings
    # Environment variables should take precedence over file config in a typical 12-factor app,
    # but the prompt says "The service must read keys only from environment variables or the config file".
    # And "expect the service to pick those keys up without manual code changes" (from config.md).
    # So we should probably prioritize config.md if it exists and has values, or merge them.
    # Pydantic Settings priority: arguments > env vars > secrets > config file > defaults.
    # So passing as arguments will override env vars.
    
    return Settings(**clean_config)

settings = get_settings()
