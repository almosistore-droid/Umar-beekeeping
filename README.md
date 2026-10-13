# 🐝 Пасека — Telegram Mini App для управления пасекой

Система учёта ульев, семей, маток, осмотров, болезней, мёда, финансов и годовых отчётов.
Работает внутри Telegram как Mini App.

**Стек:** React + TypeScript + Vite · FastAPI + SQLAlchemy 2 + Alembic · PostgreSQL · aiogram · Docker + Nginx

## Статус разработки

| Этап | Содержание | Статус |
|---|---|---|
| 1 | Структура, Docker, PostgreSQL, FastAPI, React, вход через Telegram | ✅ готово |
| 2 | Пользователи, пасеки, ульи, семьи, матки, история изменений | ✅ готово |
| 3 | Осмотры, болезни, обработки, подкормки, напоминания, хронология улья | ✅ готово |
| 4 | Мёд и статистика, продукция, роение, отводки, объединение, перемещения, зимовка | ✅ готово |
| 5 | QR-коды, сканер, deep link | ✅ готово |
| 6 | Дашборд, статистика, годовой отчёт | ✅ готово |
| 7 | CRM: клиенты, заказы, продажи и оплаты, долги, расходы, прибыль | ✅ готово |
| + | Админ-панель: доступ, приглашения, обзор системы, журнал действий | ✅ готово |
| 8 | Уведомления и напоминания в Telegram | ⏳ |
| 9 | Фото, журнал изменений, права | ⏳ |
| 10 | Тестирование, безопасность, оптимизация | ⏳ |

---

## Проверка на ноутбуке

Пошагово: **[docs/TESTING.md](docs/TESTING.md)** — запуск одной командой `docker compose -f docker-compose.dev.yml up --build`, демо-данные, вход в браузере, чек-лист проверки и тест внутри Telegram через временный туннель.

---

## Установка на сервер

Нужно: VPS с Ubuntu 22.04+, домен, направленный на IP сервера (A-запись), открытые порты 80 и 443.

### 1. Создайте бота и Mini App

1. В Telegram откройте **@BotFather** → `/newbot` → сохраните **токен**.
2. `/newapp` → выберите бота → укажите URL `https://ВАШ_ДОМЕН` → задайте короткое имя (например `app`).
3. Узнайте свой Telegram ID у **@userinfobot** — вы будете администратором.

### 2. Установите Docker и загрузите проект

```bash
curl -fsSL https://get.docker.com | sh
# загрузите папку beekeeping-app на сервер, например в /opt/beekeeping-app
cd /opt/beekeeping-app
```

### 3. Заполните `.env`

```bash
cp .env.example .env
nano .env
```

Обязательно заполнить: `DOMAIN`, `POSTGRES_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`,
`TELEGRAM_WEBAPP_SHORT_NAME`, `ADMIN_TELEGRAM_IDS`, `JWT_SECRET` (сгенерировать: `openssl rand -hex 32`).

### 4. Получите HTTPS-сертификат (Let's Encrypt)

Telegram открывает Mini App только по HTTPS.

```bash
apt install -y certbot
certbot certonly --standalone -d ВАШ_ДОМЕН --agree-tos -m ВАШ_EMAIL --non-interactive
```

Автопродление (сертификат действует 90 дней):

```bash
echo '0 3 * * * root certbot renew --webroot -w /var/lib/docker/volumes/beekeeping_certbot-www/_data --quiet --deploy-hook "docker exec beekeeping-nginx-1 nginx -s reload"' > /etc/cron.d/certbot-bee
```

### 5. Запуск

```bash
docker compose up -d --build
docker compose ps            # все сервисы должны быть Up
docker compose logs -f backend
```

Миграции базы применяются автоматически при старте backend.

### 6. Проверка

- `https://ВАШ_ДОМЕН/api/health` → `{"status":"ok","database":"ok"}`
- `https://ВАШ_ДОМЕН/api/docs` → Swagger
- В Telegram откройте бота → `/start` → **🐝 Открыть пасеку** → увидите своё имя и роль «Администратор».

Если открыть сайт в обычном браузере, будет экран «Откройте в Telegram» — так и должно быть.

### Демо-данные (по желанию)

2 пасеки, 10 ульев, матки — чтобы сразу посмотреть интерфейс:

```bash
docker compose exec backend python -m app.utils.seed --telegram-id ВАШ_TELEGRAM_ID
```

### Обновление

```bash
cd /opt/beekeeping-app
git pull                       # или замените файлы новой версией (кроме .env)
docker compose up -d --build   # миграции базы применятся автоматически
```

### Резервная копия базы

```bash
docker compose exec postgres pg_dump -U bee beekeeping | gzip > backup_$(date +%F).sql.gz
```

---

## Безопасность входа

- Клиент отправляет на сервер только подписанную строку `Telegram.WebApp.initData`.
- Сервер проверяет подпись HMAC-SHA256 с ключом бота и срок действия; без валидной подписи вход невозможен.
- После проверки выдаётся JWT. Роль всегда берётся из базы, а не из токена.
- Роль ADMIN получают только Telegram ID из `ADMIN_TELEGRAM_IDS`; остальные — `DEFAULT_USER_ROLE`.
- Nginx: HTTPS, HSTS, CSP, ограничение частоты запросов (вход — 10/мин с IP, API — 20/с).
- PostgreSQL недоступен снаружи Docker-сети. Все секреты — только в `.env`.

Роли: `ADMIN` — всё; `BEEKEEPER` — ведение пасеки; `ASSISTANT` — внесение записей; `VIEWER` — только просмотр.

---

## Локальная разработка

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp ../.env.example .env   # укажите DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/beekeeping
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend (в другом терминале)
cd frontend
npm install
npm run dev
```

Чтобы открыть приложение в обычном браузере без Telegram, сгенерируйте подписанный initData
вашим токеном (проверка подписи при этом не отключается):

```bash
cd backend && .venv/bin/python -m app.utils.dev_init_data ВАШ_TELEGRAM_ID --first-name Иван
# результат вставьте в frontend/.env.local: VITE_DEV_INIT_DATA=...
```

Демо-данные локально: `cd backend && .venv/bin/python -m app.utils.seed`

### Тесты

```bash
cd backend && .venv/bin/pytest       # нужна PostgreSQL-база beekeeping_test (TEST_DATABASE_URL)
cd frontend && npm test
```

## Разработка через Spec Kit

В проект подключён [GitHub Spec Kit](https://github.com/github/spec-kit):
- `.specify/memory/constitution.md` — «конституция»: принципы, которые нельзя нарушать;
- `docs/requirements.md` — исходное ТЗ;
- `specs/NNN-название/` — спецификация, план и задачи каждого этапа;
- команды Claude Code: `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement` и др.

Установка CLI (не обязательна для работы приложения): `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

## GitHub CI

`.github/workflows/ci.yml` при каждом push запускает тесты backend на PostgreSQL, проверку миграций,
тесты и сборку frontend.

## Структура

```
backend/   FastAPI: app/{models,schemas,routers,services,repositories,auth,utils}, alembic/, tests/
frontend/  React Mini App: src/{components,pages,layouts,hooks,services,api,types,utils,router}
bot/       Telegram-бот (aiogram): кнопка открытия Mini App, позже — уведомления
docs/      ТЗ проекта
specs/     Спецификации этапов (Spec Kit)
.specify/  Конституция, шаблоны и скрипты Spec Kit
nginx/     Внешний прокси: HTTPS, маршрутизация, rate limiting
```
