from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    bot_token: SecretStr
    daily_free_limit: int = 20  # Кількість безкоштовних завантажень на день

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()