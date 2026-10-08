from typing import List, Optional
from secrets import token_urlsafe
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "KORAS Agentic Core"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API & Security
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./koras.db")
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    # Agent Runtime constraints (Section 66)
    MAX_AGENT_STEPS: int = 10
    MAX_TOOL_CALLS: int = 15
    MAX_EXECUTION_TIME_SECONDS: int = 60
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.75
    CLARIFICATION_THRESHOLD: float = 0.50
    
    # Vulnerable User Mode
    ENABLE_VULNERABLE_USER_MODE_BY_DEFAULT: bool = False
    
    # AI Providers
    LLM_PROVIDER: str = "local_heuristic"  # Options: local_heuristic, huggingface, openai, gemini
    ASR_PROVIDER: str = "system"
    TTS_PROVIDER: str = "system"
    
    # MCP
    MCP_ENABLED: bool = True
    MCP_SERVER_HOST: str = "127.0.0.1"
    MCP_SERVER_PORT: int = 8765

    # Financial providers are intentionally disabled until a partner connector
    # has completed its legal, security and reconciliation validation (V3).
    ENABLE_FINANCIAL_CONNECTORS: bool = False

    @model_validator(mode="after")
    def ensure_secret_key(self) -> "Settings":
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            self.DEBUG = False
        if self.SECRET_KEY:
            return self
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            raise ValueError("SECRET_KEY must be configured in production")
        self.SECRET_KEY = token_urlsafe(32)
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
