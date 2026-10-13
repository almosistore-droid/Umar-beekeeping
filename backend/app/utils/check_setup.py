"""Self-check of the running backend's configuration (never prints secrets).

    docker compose -f docker-compose.dev.yml exec backend python -m app.utils.check_setup

Shows which bot the server's TELEGRAM_BOT_TOKEN belongs to, so a
"initData signature is invalid" error can be traced to a wrong / unread token.
"""
import json
import urllib.error
import urllib.request

from sqlalchemy import text

from app.config import get_settings

OK, BAD, WARN = "✅", "❌", "⚠️"


def _bot_info(token: str) -> tuple[str, str]:
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=10) as r:
            data = json.load(r)
        bot = data.get("result", {})
        return OK, f"токен принадлежит боту @{bot.get('username')} ({bot.get('first_name')})"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 404):
            return BAD, "Telegram отклонил токен: он неверный или устарел. Скопируйте заново в @BotFather → API Token"
        return WARN, f"Telegram ответил ошибкой {exc.code}"
    except Exception:  # no internet from the container
        return WARN, "не удалось связаться с Telegram для проверки (нет интернета?)"


def main() -> None:
    s = get_settings()
    print("\nПроверка настроек сервера\n" + "-" * 40)

    token = s.telegram_bot_token.strip()
    if not token:
        print(f"{BAD} TELEGRAM_BOT_TOKEN пустой")
    elif "local-test" in token or "local-dev" in token:
        print(f"{BAD} Сервер использует ТЕСТОВЫЙ токен — ваш .env не прочитан.")
        print("   Файл должен называться ровно .env (не .env.txt) и лежать в папке Umar-beekeeping.")
        print("   После исправления: docker compose -f docker-compose.dev.yml --profile telegram up -d --force-recreate backend")
    else:
        print(f"{OK} Токен задан, ID бота: {token.split(':')[0]}")
        mark, info = _bot_info(token)
        print(f"{mark} {info}")
        if token != s.telegram_bot_token:
            print(f"{WARN} В токене есть лишние пробелы — уберите их в .env")

    if s.admin_telegram_ids:
        print(f"{OK} Администраторы (Telegram ID): {', '.join(map(str, s.admin_telegram_ids))}")
    else:
        print(f"{WARN} ADMIN_TELEGRAM_IDS пустой — новые пользователи будут только наблюдателями")

    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"{OK} База данных работает")
    except Exception as exc:
        print(f"{BAD} База данных недоступна: {exc.__class__.__name__}")

    print("-" * 40)
    print("Приложение должно открываться кнопкой меню именно у того бота, который указан выше.\n")


if __name__ == "__main__":
    main()
