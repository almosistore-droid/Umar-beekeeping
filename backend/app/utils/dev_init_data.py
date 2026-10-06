"""Print a correctly signed initData string for local development.

Lets you open the Mini App in a normal browser (outside Telegram) without any
auth bypass: the string is signed with your real TELEGRAM_BOT_TOKEN from .env and
goes through the same validation as production.

    python -m app.utils.dev_init_data 123456789 --first-name Ivan --start-param hive_<uuid>

Put the output into frontend/.env.local as VITE_DEV_INIT_DATA=... (dev builds only).
"""
import argparse
import json
import time

from app.auth.telegram import sign_init_data
from app.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("telegram_id", type=int)
    parser.add_argument("--first-name", default="Dev")
    parser.add_argument("--username", default=None)
    parser.add_argument("--start-param", default=None)
    args = parser.parse_args()

    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit("Refusing to generate dev initData in production")
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

    user = {"id": args.telegram_id, "first_name": args.first_name}
    if args.username:
        user["username"] = args.username
    fields = {"auth_date": str(int(time.time())), "user": json.dumps(user, separators=(",", ":"))}
    if args.start_param:
        fields["start_param"] = args.start_param
    print(sign_init_data(fields, settings.telegram_bot_token))


if __name__ == "__main__":
    main()
