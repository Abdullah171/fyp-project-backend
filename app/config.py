# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://netsentinel:netsentinel@db:5432/netsentinel"
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    SEARCH_PROVIDER: str = "wikipedia"

    class Config:
        env_file = ".env"


settings = Settings()
