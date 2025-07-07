from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expiry_minutes: int = 30
    refresh_token_expiry_days: int = 7

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str

    gemini_api_key: str

    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
