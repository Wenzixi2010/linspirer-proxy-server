import os
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LINSPIRER_KEY: str
    LINSPIRER_IV: str
    LINSPIRER_TARGET_URL: str = "https://cloud.linspirer.com:883"
    LINSPIRER_DB_PATH: str = "sqlite+aiosqlite:///./data/linspirer.db"
    LINSPIRER_HOST: str = "0.0.0.0"
    LINSPIRER_PORT: int = 8080
    LINSPIRER_JWT_SECRET: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
