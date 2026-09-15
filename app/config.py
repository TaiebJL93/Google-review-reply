import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Accepts the `postgres://` scheme some hosts (Neon, Heroku-style) emit.

    SQLAlchemy 2.x only recognises `postgresql://`; without this a pasted
    Neon connection string fails at engine creation with "Can't load plugin".
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.database_url = _normalize_database_url(
            os.environ.get("DATABASE_URL", "sqlite:///./reviewreply.db")
        )
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self.google_redirect_uri = os.environ.get(
            "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"
        )

        # Signs the session cookie that keeps a user logged in. Render generates
        # one per service (see render.yaml); locally an unset value falls back
        # to a per-process random key, which just means sessions reset whenever
        # the dev server restarts.
        self.secret_key = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

        # Render sets RENDER=true in every deploy; use it to mark the session
        # cookie Secure so browsers only send it over HTTPS in production.
        self.secure_cookies = os.environ.get("RENDER", "").lower() == "true"


settings = Settings()
