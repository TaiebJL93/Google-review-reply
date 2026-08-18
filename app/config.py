import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./reviewreply.db")
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self.google_redirect_uri = os.environ.get(
            "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"
        )


settings = Settings()
