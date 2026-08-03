import os


class Settings:
    def __init__(self) -> None:
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./reviewreply.db")


settings = Settings()
