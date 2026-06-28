from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # sobrescrever variaveis pelo .env da aplicação
    # Banco
    database_url: str = "postgresql+psycopg://raizes:raizes@localhost:5432/raizes"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v
    database_replica_url: str | None = None

    # cache
    redis_url: str = "redis://localhost:6379/0"
    menu_cache_ttl_seconds: int = 120

    # mensageria
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # strategy de pagamento
    payment_gateway: str = "PIX"
    payment_webhook_secret: str = "troque-este-segredo"

    # autenticação
    app_env: str = "development"
    jwt_secret: str = "troque-este-segredo"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    #redenciais do admin criado pelo seed
    admin_seed_email: str = "admin@raizesdonordeste.com.br"
    admin_seed_senha: str = "admin123"


settings = Settings()
