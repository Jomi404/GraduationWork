import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    db_user: str = Field(default="user")
    db_password: str = Field(default="")
    db_host: str = Field(default="localhost")
    db_port: str = Field(default="8000")
    db_name: str = Field(default="postgresql")
    telegram_token: str
    provider_token: str
    currency: str

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")


settings = Settings()
database_url = settings.DB_URL
