import os


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


BOT_TOKEN = _required("TELEGRAM_BOT_TOKEN")
# Backend inside the Docker network: login confirmation for the app installed on the phone
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000").rstrip("/")
# Public HTTPS URL of the Mini App, e.g. https://bee.example.com (server).
# Dev: the tunnel writes its current address to WEBAPP_URL_FILE instead.
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip().rstrip("/")
WEBAPP_URL_FILE = os.environ.get("WEBAPP_URL_FILE", "").strip()
# 0 = do not touch the menu button (dev: the tunnel manages it)
SET_MENU_BUTTON = os.environ.get("SET_MENU_BUTTON", "1").strip() != "0"

if not WEBAPP_URL and not WEBAPP_URL_FILE:
    raise SystemExit("Environment variable WEBAPP_URL is required")


def webapp_url() -> str | None:
    """Current address of the Mini App (re-read in dev: the tunnel address changes)."""
    if WEBAPP_URL_FILE:
        try:
            with open(WEBAPP_URL_FILE, encoding="utf-8") as f:
                url = f.read().strip().rstrip("/")
            if url.startswith("https://"):
                return url
        except OSError:
            pass
    return WEBAPP_URL or None
