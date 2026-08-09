from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = Field(default="ctf-agent-range", alias="PROJECT_NAME")
    backend_port: int = Field(default=18080, alias="BACKEND_PORT")
    database_url: str = Field(default="mysql+pymysql://ctf_agent:ctf_agent_dev@mysql:3306/ctf_agent", alias="DATABASE_URL")
    instance_port_min: int = Field(default=18000, alias="INSTANCE_PORT_MIN")
    instance_port_max: int = Field(default=18999, alias="INSTANCE_PORT_MAX")
    instance_public_host: str = Field(default="localhost", alias="INSTANCE_PUBLIC_HOST")
    instance_public_port_offset: int = Field(default=0, alias="INSTANCE_PUBLIC_PORT_OFFSET")
    instance_ttl_seconds: int = Field(default=3600, alias="INSTANCE_TTL_SECONDS")
    instance_network_prefix: str = Field(default="ctf-agent-range", alias="INSTANCE_NETWORK_PREFIX")
    challenge_image_prefix: str = Field(default="ctf-agent-range", alias="CHALLENGE_IMAGE_PREFIX")
    secret_key: str = Field(default="change-me-in-local-env", alias="SECRET_KEY")
    api_base_url: str = Field(default="http://localhost:18080", alias="API_BASE_URL")
    frontend_api_base_url: str = Field(default="http://localhost:18080", alias="FRONTEND_API_BASE_URL")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def challenge_registry_path(self) -> Path:
        return self.project_root / "challenge-registry" / "challenges.yaml"

    @property
    def challenge_root(self) -> Path:
        return self.project_root / "challenges"


@lru_cache
def get_settings() -> Settings:
    return Settings()
