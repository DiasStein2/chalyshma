from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Olympiad Desk"
    database_url: str = "sqlite:///./olympiad.db"
    jwt_secret: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    seed_admin_password: str = "admin123"
    seed_lead_password: str = "lead1234"
    app_timezone: str = "Asia/Almaty"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
