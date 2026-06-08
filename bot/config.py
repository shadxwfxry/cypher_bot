from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Any, Optional

class Settings(BaseSettings):
    # Telegram bot token and support manager telegram username contact
    bot_token: str = Field(alias="BOT_TOKEN")
    support_username: str = Field(default="sup_cypher", alias="SUPPORT_USERNAME")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Admin configurations
    admin_ids: list[int] = Field(default=[], alias="ADMIN_IDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> list[int]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v
    
    # PostgreSQL cluster configurations (utilized in standard production setups)
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_host: str = Field(default="postgres", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="cypher_db", alias="DB_NAME")
    
    # Direct DB connection URL (overrides individual credentials, enabling MySQL/PostgreSQL driver switching)
    db_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    # Redis cache integration configurations for FSM storage and background task queue queues
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    
    # External marketplace core API endpoints credentials
    external_api_url: str = Field(default="http://localhost:8000", alias="EXTERNAL_API_URL")
    external_api_token: str = Field(alias="EXTERNAL_API_TOKEN")
    
    # Tor Proxy configuration for hidden services
    tor_proxy: str = Field(default="socks5://127.0.0.1:9050", alias="TOR_PROXY")
    
    # Webhook server parameters (enforces signature handshake verification)
    webhook_port: int = Field(default=8080, alias="WEBHOOK_PORT")
    webhook_secret: str = Field(alias="WEBHOOK_SECRET")

    @property
    def database_url(self) -> str:
        """Assembles custom connection URL string for SQLAlchemy engine usage, prioritizing direct override URL."""
        if self.db_url_override:
            return self.db_url_override
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """Assembles standard Redis connection URL string."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # Configuration mappings pointing to default .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

