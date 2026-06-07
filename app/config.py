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

    # Ambiente de dados: simulated | real | auto
    data_mode: str = "simulated"
    real_data_ttl_s: int = 90

    # SCOR — names only, never values here
    scor_token: str = ""
    scor_endpoint: str = ""

    # Auth
    ops_secret: str = "change-me"

    # Database
    database_url: str = "postgresql+asyncpg://goncalomelodemagalhaes@localhost/plantaos"

    # MQTT — device control bridge
    mqtt_host:     str = "localhost"
    mqtt_port:     int = 1883
    mqtt_user:     str = "plantaos"
    mqtt_password: str = ""

    # Public URL (OTA firmware serving)
    public_url: str = "http://localhost:8000"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://www.plantarockinrio.com",
        "https://plantarockinrio.com",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
