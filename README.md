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
| + | Два языка: русский и тоҷикӣ (экраны, ошибки, отчёты, QR-этикетки, бот) | ✅ готово |
| + | Приложение на телефоне (iPhone, Android): значок на экране, вход через бота, сканер камерой | ✅ готово |
| + | Вход по логину и паролю для тех, у кого нет Telegram | ✅ готово |
| 8 | Уведомления и напоминания в Telegram | ✅ готово |
| + | Склад: рамки, вощина, проволока, корм, лекарства; нормы расхода, автоматическое списание | ✅ готово |
| + | Работа без интернета: осмотры, подкормки, обработки сохраняются в телефоне и отправляются сами | ✅ готово |
| + | Календарь вывода маток: шаги от дня прививки, напоминания, учёт принятых, вышедших и плодных | ✅ готово |
| + | Панель владельца подписки: все клиенты, сроки оплаты, продление одной кнопкой | ✅ готово |
| + | Подписка: у каждого клиента своё приложение (название, логотип, цвет, домен, бот), блокировка без оплаты | ✅ готово |
| 9 | Фото, журнал изменений, права | ⏳ |
| 10 | Тестирование, безопасность, оптимизация, выпуск на сервер | ✅ готово (проверки повторить после этапа 9) |

---

## Проверка на ноутбуке

Пошагово: **[docs/TESTING.md](docs/TESTING.md)** — запуск одной командой `docker compose -f docker-compose.dev.yml up --build`, демо-данные, вход в браузере, чек-лист проверки и тест внутри Telegram через временный туннель.

---

## Приложение на телефоне (iPhone и Android)

Кроме мини-приложения в Telegram, пасеку можно открывать **значком на главном экране телефона** (PWA) —
без App Store и Google Play. Нужен адрес по HTTPS: на сервере это ваш домен, на ноутбуке — адрес туннеля
(он меняется после сна ноутбука, поэтому для постоянной работы нужен сервер).

- **Установка.** iPhone: откройте адрес в **Safari** → «Поделиться» → «На экран «Домой»». Android: откройте в
  **Chrome** → «Установить приложение» (или кнопка «Установить на телефон» на экране входа). В мини-приложении:
  «Ещё → Приложение на телефоне → Открыть в браузере».
- **Вход без пароля.** «Войти через Telegram» открывает бота с одноразовым кодом; в боте нажмите «Войти» и
  вернитесь в приложение. Аккаунт, роль и данные — те же, что в мини-приложении. Телефон остаётся в системе,
  пока не нажать «Ещё → Выйти на этом устройстве» или пока администратор не заблокирует пользователя.
- **Без Telegram — по логину и паролю.** Администратор: «Ещё → Админ-панель → Пользователи → ＋ Добавить →
  Логин и пароль» → имя, логин, роль → временный пароль (показывается один раз, кнопка «Отправить человеку»).
  При первом входе человек придумывает свой пароль. Забыл пароль — администратор нажимает «Новый пароль».
  Человеку с Telegram тоже можно выдать логин («Вход по паролю»): аккаунт один, входов два.
- **Сканер** открывает камеру телефона прямо в приложении.
- Для входа должен работать бот (сервис `bot`) и быть указан `TELEGRAM_BOT_USERNAME`. Бот с одним токеном
  может работать только в одном месте: на ноутбуке или на сервере.

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

Обязательно заполнить: `DOMAIN`, `POSTGRES_PASSWORD` (только латинские буквы и цифры: символы `@ / : # ? %` ломают адрес базы), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`,
`TELEGRAM_WEBAPP_SHORT_NAME`, `ADMIN_TELEGRAM_IDS`, `JWT_SECRET` (не короче 32 символов; вписать сразу:
`sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 32)/" .env`).
На сервере с 2 ГБ памяти добавьте файл подкачки на 2 ГБ — без него сборка экранов может упасть.

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

В обычном браузере открывается экран входа (логин и пароль или «Войти через Telegram») — оттуда же приложение ставится значком на телефон.

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

## Клиенты подписки (несколько приложений на одном сервере)

У каждого клиента своя копия: своя база, домен, HTTPS, бот, название, логотип и цвет. Код и образы общие,
впереди один nginx (`deploy/edge`). Всё делает `./deploy/client.sh` (без аргументов — список команд).

```bash
cd /opt/beekeeping && git pull
./deploy/client.sh build                 # собрать новую версию (один раз для всех)
./deploy/client.sh add asal asal.tj      # новый клиент → clients/asal.env (30 дней пробно)
nano clients/asal.env                    # BRAND_NAME, BRAND_COLOR, SUBSCRIPTION_CONTACT, токен бота, ADMIN_TELEGRAM_IDS
./deploy/client.sh logo asal /root/asal.png
./deploy/client.sh start asal            # DNS asal.tj → IP сервера должен быть уже настроен
./deploy/client.sh extend asal +1year    # оплатил — продлить; block asal — закрыть сейчас
./deploy/client.sh list                  # кто до какого числа оплачен
./deploy/client.sh update all            # после build: все клиенты на новой версии
```

После даты `SUBSCRIPTION_UNTIL` приложение клиента закрыто для всех (экран «Подписка закончилась» с вашим
контактом), данные сохраняются; за 7 дней администратор клиента видит предупреждение.

### Готовность сервера к работе (этап 10) — один раз

```bash
./deploy/harden.sh                       # файрвол (SSH, 80, 443), fail2ban, автообновления Ubuntu
./deploy/client.sh backup-setup          # токен бота и ваш Telegram ID → копии будут приходить вам; покажет ПАРОЛЬ КОПИЙ
./deploy/client.sh backup all --send     # проверка: в Telegram пришёл файл .enc
./deploy/client.sh cron                  # копии 02:30, сертификаты 03:00, проверка каждые 15 минут
./deploy/client.sh check                 # «Всё в порядке»
```

- Копии баз: каждую ночь зашифрованный файл (AES-256) приходит вам в Telegram, ещё 30 дней лежит на сервере.
  Пароль копий записан только в `deploy/backup.env` и у вас — без него копию не открыть.
- Открыть копию из Telegram на сервере: `./deploy/client.sh decrypt asal-2026-10-18-0230.sql.gz.enc`;
  вернуть базу клиента: `./deploy/client.sh restore asal backups/asal-….sql.gz` (сначала сам сделает копию текущих данных).
- `update all` перед перезапуском делает копии; если новая версия не работает — `./deploy/client.sh rollback`.
- Проблема (приложение не отвечает, сертификат истекает, диск заполнен > 85 %) — сообщение вам в Telegram,
  повтор не чаще раза в 6 часов.
- Вход по SSH только по ключу: `./deploy/harden.sh --ssh-keys-only` (пароли отключаются, только если ключ уже стоит).

**Панель владельца** — все клиенты в одном окне (ульи, пользователи, мёд, последний вход, срок оплаты) и продление
одной кнопкой: `./deploy/client.sh owner admin.ВАШ_ДОМЕН` (DNS-запись A для admin.… → IP сервера). Пароль
показывается один раз; новый — `./deploy/client.sh owner-password`.

Старую установку (одна копия, `.env` в корне) переводит в клиенты `./deploy/client.sh adopt fayzi` — база и
файлы остаются (тот же Docker-проект `beekeeping`). Подробности: `specs/013-subscription-clients/spec.md`.

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

`.github/workflows/ci.yml` при каждом push: тесты backend на PostgreSQL с покрытием не ниже 90 %, проверку
миграций, поиск известных уязвимостей в пакетах (pip-audit backend и бота, npm audit того, что уходит на телефоны),
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
