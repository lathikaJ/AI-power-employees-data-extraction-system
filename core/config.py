from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
