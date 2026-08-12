import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./reviewreply.db")


settings = Settings()
