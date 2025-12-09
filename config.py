import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = pathlib.Path(__file__).parent
ENV_PATH = BASE_DIR / "./.env"


class Settings(BaseSettings):
    # DB_HOST: str = Field(..., env="DB_HOST")
    # DB_PORT: int = Field(..., env="DB_PORT")
    # DB_USER: str = Field(..., env="DB_USER")
    # DB_PASS: str = Field(..., env="DB_PASS")
    # DB_NAME: str = Field(..., env="DB_NAME")

    # # REDIS_HOST: str = Field(..., env="REDIS_HOST")
    # # REDIS_PORT: str = Field(..., env="REDIS_PORT")
    # # REDIS_PASS: str = Field(..., env="REDIS_PASS")

    # SECRET_KEY: str = Field(..., env="SECRET_KEY")

    # AUTH_TOKEN_EXPIRES: int = Field(..., env="AUTH_TOKEN_EXPIRES")

    # BOT_TOKEN: str = Field(..., env="BOT_TOKEN")

    # GUARD_HASH_SECRET: str = Field(..., env="GUARD_HASH_SECRET")
    # SMTP_LOGIN: str = Field(..., env="SMTP_LOGIN")
    # SMTP_PASSWORD: str = Field(..., env="SMTP_PASSWORD")

    # ADMIN_TOKEN: str = Field(..., env="ADMIN_TOKEN")

    RU_CAPTCHA_KEY: str = Field(..., env="RU_CAPTCHA_KEY")

    @property
    def DB_URL(self):
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASS}@"
            f"{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
