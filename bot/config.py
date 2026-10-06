import os


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


BOT_TOKEN = _required("TELEGRAM_BOT_TOKEN")
# Public HTTPS URL of the Mini App, e.g. https://bee.example.com
WEBAPP_URL = _required("WEBAPP_URL").rstrip("/")
