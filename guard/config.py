from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./guard.db"
    portal_database_url: str = "sqlite:///./portal.db"
    app_base_url: str = "http://localhost:8080"
    portal_base_url: str = "http://172.30.90.2:8090"
    portal_internal_url: str = "http://portal-admin:8091"
    worker_internal_url: str = "http://worker:8092"
    worker_shared_auth_secret: str = ""
    portal_admin_secret: str = ""
    session_secret: str = ""
    operator_username: str = "operator"
    operator_password: str = ""
    demo_mode: bool = True
    cookie_secure: bool = False
    vultr_inference_api_key: str = ""
    vultr_inference_base_url: str = "https://api.vultrinference.com/v1"
    vultr_chat_model: str = ""
    vultr_vision_model: str = ""
    artifact_dir: str = "./artifacts"
    sandbox_image: str = "skg-browser:local"
    sandbox_network: str = "skg-execution"
    sandbox_deadline: int = 90
    max_job_seconds: int = 900


@lru_cache
def settings() -> Settings:
    return Settings()
