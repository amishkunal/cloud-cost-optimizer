from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    env: str = "dev"

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "ccopt"
    db_password: str = "ccoptpassword"
    db_name: str = "ccopt_db"

    redis_host: str = "localhost"
    redis_port: int = 6379

    openai_api_key: str | None = None

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",  # Allow extra environment variables (e.g., AWS_*)
    )


settings = Settings()
