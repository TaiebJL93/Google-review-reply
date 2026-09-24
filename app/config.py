import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Accepts the `postgres://` scheme some hosts (e.g. Neon) hand out.

    SQLAlchemy 2.x only recognises `postgresql://`; without this a pasted
    connection string fails at engine creation with "Can't load plugin".
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        # SQLite locally; the Cloudflare-hosted container gets a Neon Postgres
        # URL instead, because container disks are wiped on every restart.
        self.database_url = _normalize_database_url(
            os.environ.get("DATABASE_URL", "sqlite:///./reviewreply.db")
        )
        self.google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self.google_redirect_uri = os.environ.get(
            "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"
        )

        # Signs the session cookie that keeps a user logged in. An unset value
        # falls back to a per-process random key, which just means everyone is
        # logged out whenever the server restarts. Set it in .env to keep sessions.
        self.secret_key = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)

        # Marks the session cookie Secure so browsers only send it over HTTPS.
        # Set by scripts/start-public.ps1 (tunnel) and by cloudflare/wrangler.jsonc
        # (hosted); leave it off for plain http://127.0.0.1 use.
        self.secure_cookies = os.environ.get("SECURE_COOKIES", "").lower() == "true"


settings = Settings()
