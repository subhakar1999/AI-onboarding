from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentForge Enterprise Engine"
    ENV: str = "production"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://agentforge_admin:SecurePass123!@localhost:5432/agentforge_db"
    
    # LLM Providers
    OPENAI_API_KEY: str = "sk-mock-key-for-dev"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    
    # Security
    SECRET_KEY: str = "SUPER_SECRET_ENTERPRISE_SIGNING_KEY_CHANGE_IN_PROD"
    CORS_ORIGINS: List[str] = ["*"]
    
    # SMTP Config for Magic Links
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@agentforge.local"

    # Cost Engine Catalog (USD per 1 Million Tokens)
    MODEL_RATES: dict = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "meta-llama-3-3-70b": {"input": 0.40, "output": 0.80}
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()