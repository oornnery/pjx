"""Application settings — loaded from environment variables."""

import os


class Settings:
    PROJECT_NAME: str = "PJX Demo"
    SECRET_KEY: str = os.environ.get("PJX_SECRET_KEY", "change-me-in-production")
    HOST: str = "127.0.0.1"
    PORT: int = 8000


settings = Settings()
