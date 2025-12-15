"""
Configuration settings for the application.
Loads environment variables and provides typed settings.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Personal Finance Tracker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://financeuser:financepass@db:5432/financedb"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS (Cross-Origin Resource Sharing)
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",
        "http://localhost:8081"
    ]
    
    class Config:
        """Pydantic config to load from .env file."""
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()