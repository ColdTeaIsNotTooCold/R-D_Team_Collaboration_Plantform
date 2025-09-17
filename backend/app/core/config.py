from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "Team Collaboration Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://user:password@localhost/team_collaboration_db"

    # Redis - 增强配置
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_decode_responses: bool = True

    # Cache settings
    cache_ttl: int = 3600  # 1 hour default cache time
    cache_prefix: str = "tcp:"

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="BACKEND_CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()