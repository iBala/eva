"""
Configuration management for Eva Assistant.

This module handles loading environment variables and provides centralized
configuration for the entire application.
"""

import os
from typing import List
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Eva's Gmail Account Configuration
    eva_gmail_client_id: str
    eva_gmail_client_secret: str
    eva_gmail_refresh_token: str = ""
    
    # Google OAuth Configuration for User Calendar Connections
    # These are used when users connect their calendars through the app
    google_oauth_client_id: str
    google_oauth_client_secret: str
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Database Configuration
    database_url: str = "sqlite:///./data/eva.db"
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"
    
    # Email Processing Configuration
    email_poll_interval: int = 60  # seconds
    email_response_timeout: int = 300  # seconds
    
    # Security Configuration
    secret_key: str
    
    # OAuth Scopes
    eva_gmail_scopes: List[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]
    
    # Scopes for user calendar connections (READ-ONLY)
    user_calendar_scopes: List[str] = [
        "https://www.googleapis.com/auth/calendar.readonly"
    ]
    
    # Data directories
    data_dir: Path = Path("./data")
    oauth_dir: Path = Path("./oauth")
    token_dir: Path = Path("./oauth/tokens")
    user_tokens_dir: Path = Path("./data/user_tokens")  # For user calendar tokens
    
    @field_validator('data_dir', 'oauth_dir', 'token_dir', 'user_tokens_dir')
    @classmethod
    def create_directories(cls, v):
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_eva_oauth_config() -> dict:
    """Get OAuth configuration for Eva's Gmail account."""
    return {
        "client_id": settings.eva_gmail_client_id,
        "client_secret": settings.eva_gmail_client_secret,
        "scopes": settings.eva_gmail_scopes,
        "token_file": settings.token_dir / "eva_gmail_token.json"
    }


def get_user_oauth_config(user_id: str) -> dict:
    """
    Get OAuth configuration for a user's calendar connection.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dict containing OAuth configuration for user calendar connection
    """
    return {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "scopes": settings.user_calendar_scopes,
        "token_file": settings.user_tokens_dir / f"user_{user_id}_calendar_token.json"
    } 