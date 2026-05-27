from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PlantaOS"
    app_version: str = "0.1.0"
    debug: bool = False
    port: int = 8000
    simulation_active: bool = True

    # SCOR — names only, never values here
    scor_token: str = ""
    scor_endpoint: str = ""

    # Auth
    ops_secret: str = "change-me"

    # Database (optional for phase 0)
    database_url: str = "sqlite+aiosqlite:///./plantaos.db"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
