import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = pathlib.Path(__file__).parent
ENV_PATH = BASE_DIR / "./.env"


class Settings(BaseSettings):
    RU_CAPTCHA_KEY: str = Field(..., env="RU_CAPTCHA_KEY")

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
