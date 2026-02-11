"""
Configuration management for the FastAPI backend.
All sensitive values must be provided via environment variables.
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    IMPORTANT: Never hardcode secrets. All sensitive values must be
    provided via environment variables.
    """
    # Application settings
    app_name: str = "RADTest Backend"
    debug: bool = Field(default=False, env="DEBUG")
    max_request_size: int = Field(
        default=1_048_576,  # 1MB default
        env="MAX_REQUEST_SIZE",
        description="Maximum request size in bytes"
    )

    # Railway worker service settings
    railway_worker_url: str = Field(
        ...,
        env="RAILWAY_WORKER_URL",
        description="Railway worker service API endpoint. Must be provided via environment variables."
    )
    railway_api_token: str = Field(
        ...,
        env="RAILWAY_API_TOKEN",
        description="Railway API authentication token. Must be provided via environment variables."
    )
    railway_project_id: str = Field(
        ...,
        env="RAILWAY_PROJECT_ID",
        description="Railway project ID. Must be provided via environment variables."
    )
    railway_environment_id: str = Field(
        ...,
        env="RAILWAY_ENVIRONMENT_ID",
        description="Railway environment ID. Must be provided via environment variables."
    )
    railway_service_id: str = Field(
        ...,
        env="RAILWAY_SERVICE_ID",
        description="Railway service ID for extractor. Must be provided via environment variables."
    )

    # Supabase settings
    supabase_url: str = Field(
        ...,
        env="SUPABASE_URL",
        description="Supabase project URL. Must be provided via environment variables."
    )
    supabase_key: str = Field(
        ...,
        env="SUPABASE_KEY",
        description="Supabase API key. Must be provided via environment variables."
    )

    # API settings
    apollo_api_key: str = Field(
        ...,
        env="APOLLO_API_KEY",
        description="Apollo.io API key. Must be provided via environment variables."
    )
    pdl_api_key: str = Field(
        ...,
        env="PDL_API_KEY",
        description="PeopleDataLabs API key. Must be provided via environment variables."
    )

    # LLM settings
    openai_api_key: str = Field(
        ...,
        env="OPENAI_API_KEY",
        description="OpenAI API key for LLM agents. Must be provided via environment variables."
    )

    # Gamma API settings
    gamma_api_key: str = Field(
        ...,
        env="GAMMA_API_KEY",
        description="Gamma API key for slideshow generation. Must be provided via environment variables."
    )

    # ZoomInfo settings (optional - graceful degradation without it)
    # Preferred: use client_id + client_secret for automatic token refresh
    zoominfo_client_id: Optional[str] = Field(
        default=None,
        env="ZOOMINFO_CLIENT_ID",
        description="ZoomInfo OAuth client ID for auto-auth. Must be provided via environment variables."
    )
    zoominfo_client_secret: Optional[str] = Field(
        default=None,
        env="ZOOMINFO_CLIENT_SECRET",
        description="ZoomInfo OAuth client secret for auto-auth. Must be provided via environment variables."
    )
    zoominfo_access_token: Optional[str] = Field(
        default=None,
        env="ZOOMINFO_ACCESS_TOKEN",
        description="ZoomInfo static access token (alternative to client_id/secret). Must be provided via environment variables."
    )

    # Timeout settings
    worker_timeout: int = Field(
        default=300,
        env="WORKER_TIMEOUT",
        description="Timeout for worker API calls in seconds"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
