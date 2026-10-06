# 🐝 Пасека — Telegram Mini App для управления пасекой

Система учёта ульев, семей, маток, осмотров, болезней, мёда, финансов и годовых отчётов.
Работает внутри Telegram как Mini App.

**Стек:** React + TypeScript + Vite · FastAPI + SQLAlchemy 2 + Alembic · PostgreSQL · aiogram · Docker + Nginx

## Статус разработки

| Этап | Содержание | Статус |
|---|---|---|
| 1 | Структура, Docker, PostgreSQL, FastAPI, React, вход через Telegram | ✅ готово |
| 2 | Пользователи, пасеки, ульи, семьи, матки | ⏳ |
| 3 | Осмотры, болезни, обработки, подкормки | ⏳ |
| 4 | Мёд, продукция, роение, разделение/объединение, перемещения, зимовка | ⏳ |
| 5 | QR-коды, сканер, deep link | ⏳ |
| 6 | Дашборд, статистика, годовой отчёт | ⏳ |
| 7 | Расходы, продажи, прибыль | ⏳ |
| 8 | Уведомления и напоминания в Telegram | ⏳ |
| 9 | Фото, журнал изменений, права | ⏳ |
| 10 | Тестирование, безопасность, оптимизация | ⏳ |

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

### Обновление

```bash
cd /opt/beekeeping-app
# замените файлы новой версией (кроме .env)
docker compose up -d --build
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

### Тесты

```bash
cd backend && .venv/bin/pytest       # нужна PostgreSQL-база beekeeping_test (TEST_DATABASE_URL)
cd frontend && npm test
```

## Структура

```
backend/   FastAPI: app/{models,schemas,routers,services,repositories,auth,utils}, alembic/, tests/
frontend/  React Mini App: src/{components,pages,layouts,hooks,services,api,types,utils,router}
bot/       Telegram-бот (aiogram): кнопка открытия Mini App, позже — уведомления
nginx/     Внешний прокси: HTTPS, маршрутизация, rate limiting
```
