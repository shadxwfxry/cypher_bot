from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    support_username: str = Field(default="sup_cypher", alias="SUPPORT_USERNAME")
    debug: bool = Field(default=False, alias="DEBUG")
    
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    db_host: str = Field(default="postgres", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="cypher_db", alias="DB_NAME")
    
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    
    external_api_url: str = Field(default="http://localhost:8000", alias="EXTERNAL_API_URL")
    external_api_token: str = Field(alias="EXTERNAL_API_TOKEN")
    
    webhook_port: int = Field(default=8080, alias="WEBHOOK_PORT")
    webhook_secret: str = Field(alias="WEBHOOK_SECRET")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
