# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://netsentinel:netsentinel@db:5432/netsentinel"
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # which provider to use: "searxng" or "wikipedia"
    SEARCH_PROVIDER: str = "searxng"

    # base URL of your SearxNG instance (make sure JSON format is enabled)
    # e.g. "http://searxng:8080" if you add a docker service, or "http://localhost:8080"
    SEARXNG_URL: str = "http://searxng:8080"

    # optional: restrict categories, leave empty for all
    SEARXNG_CATEGORIES: str = "general,images"

    class Config:
        env_file = ".env"


settings = Settings()
