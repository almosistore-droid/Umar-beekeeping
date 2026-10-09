🐝 BEEKEEPING MANAGEMENT SYSTEM — TELEGRAM MINI APP

Ты — senior full-stack developer и software architect.

Твоя задача — разработать полноценную production-ready систему управления пчелиной пасекой в виде Telegram Mini App.

Система предназначена для пчеловодов и должна позволять полностью контролировать каждый улей, пчелиную семью, матку, здоровье, осмотры, мёд, подкормки, обработки, роение, зимовку, расходы и доходы.

Главный принцип системы:

Улей → Пчелиная семья → Матка → Осмотры → Здоровье → Обработки → Подкормки → Мёд → Роение → Разделение/объединение → Зимовка → Финансы → Годовой отчёт

⸻

1. ОСНОВНАЯ КОНЦЕПЦИЯ

Это не простой CRUD.

Система должна сохранять полную историческую историю каждого улья и семьи.

Нельзя терять историю при:

* замене матки;
* замене семьи;
* переносе улья;
* разделении семьи;
* объединении семей;
* изменении номера улья;
* продаже семьи;
* гибели семьи.

Каждое важное событие должно иметь:

* дату;
* время;
* пользователя;
* старое состояние;
* новое состояние;
* комментарий.

⸻

2. TECH STACK

Использовать:

Frontend

* React
* TypeScript
* Vite
* Telegram Mini Apps SDK
* React Router
* TanStack Query
* современный UI
* адаптивный mobile-first дизайн

Frontend должен быть оптимизирован прежде всего для:

* iPhone;
* Android;
* Telegram WebView.

Не делать интерфейс как обычный desktop website.

⸻

Backend

Использовать:

* Python 3.12+
* FastAPI
* SQLAlchemy 2
* Alembic
* Pydantic
* PostgreSQL

API:

REST API.

Документация:

Swagger/OpenAPI.

⸻

Telegram

Использовать:

* Telegram Bot API
* Telegram Mini App
* Telegram WebApp authentication
* Telegram WebApp initData validation.

Нельзя доверять Telegram user ID, пришедшему от клиента, без проверки initData.

⸻

QR

Каждый улей получает уникальный QR-код.

QR содержит не всю информацию, а уникальный идентификатор улья или безопасный URL.

Принцип:

QR
↓
Hive UUID
↓
Telegram Mini App
↓
Backend
↓
PostgreSQL
↓
карточка конкретного улья.

⸻

3. PROJECT STRUCTURE

Создать монорепозиторий:

beekeeping-app/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── auth/
│   │   └── utils/
│   │
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── api/
│   │   ├── types/
│   │   ├── utils/
│   │   └── router/
│   ├── package.json
│   └── vite.config.ts
│
├── bot/
│   ├── bot.py
│   └── handlers/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── CLAUDE.md

⸻

4. DATABASE

Использовать PostgreSQL.

Не хранить бизнес-данные в JSON, если для них можно сделать нормальные реляционные поля.

Использовать UUID для основных сущностей.

Создать таблицы:

users
apiaries
hives
bee_families
queens
hive_inspections
diseases
hive_diseases
treatments
feedings
honey_harvests
other_products
swarms
hive_movements
hive_splits
hive_merges
wintering
expenses
sales
tasks
photos
qr_codes
audit_logs
notifications

⸻

5. USERS

Поля:

id
telegram_id
username
first_name
last_name
role
is_active
created_at
updated_at

Роли:

ADMIN
BEEKEEPER
ASSISTANT
VIEWER

⸻

6. APIARIES

Поля:

id
name
description
address
latitude
longitude
created_at
updated_at

Один пользователь может иметь несколько пасек.

⸻

7. HIVES

Это одна из главных таблиц.

Поля:

id UUID
apiary_id
hive_number
hive_type
status
installation_date
colonization_date
current_family_id
current_queen_id
last_inspection_at
next_inspection_at
notes
created_at
updated_at

Статусы:

ACTIVE
WEAK
STRONG
SICK
QUEENLESS
EMPTY
QUARANTINE
MERGED
SPLIT
SOLD
LOST

id должен быть постоянным.

Если номер улья изменился, QR не должен ломаться.

⸻

8. BEE FAMILIES

Поля:

id
hive_id
strength
status
origin
start_date
end_date
notes
created_at
updated_at

Сила:

VERY_WEAK
WEAK
MEDIUM
STRONG
VERY_STRONG

История семей должна сохраняться.

⸻

9. QUEENS

Поля:

id
queen_code
birth_date
birth_year
breed
origin
status
current_hive_id
installed_at
removed_at
removal_reason
egg_laying_quality
swarming_tendency
temperament
notes
created_at
updated_at

Статус:

ACTIVE
GOOD
OBSERVATION
WEAK
LOST
REPLACED
DEAD
SOLD

Возраст рассчитывать автоматически.

Например:

Матка родилась: 15.06.2024
Сегодня: 06.10.2026
Возраст: 2 года 3 месяца

Не хранить возраст как постоянное поле.

Хранить дату рождения и рассчитывать возраст.

⸻

10. INSPECTIONS

Каждый осмотр должен быть отдельной записью.

Поля:

id
hive_id
user_id
inspection_date
strength
frames_total
brood_frames
honey_frames
pollen_frames
queen_present
queen_condition
egg_laying
queen_cells
swarming_signs
food_level
aggressiveness
health_status
notes
created_at

Допускается добавление фотографий.

⸻

11. HEALTH / DISEASES

Создать справочник болезней.

Примеры:

* Varroosis
* Nosemosis
* American foulbrood
* European foulbrood
* Chalkbrood
* Viral diseases
* Wax moth
* Other

Для каждого случая болезни:

hive_id
disease_id
detected_at
severity
symptoms
diagnosis
status
resolved_at
notes

Статусы:

SUSPECTED
CONFIRMED
TREATING
RESOLVED

⸻

12. TREATMENTS

Поля:

id
hive_id
disease_id
treatment_date
medication
dosage
method
performed_by
next_treatment_date
result
notes

Система должна автоматически создавать напоминание о следующей обработке.

⸻

13. FEEDINGS

Поля:

id
hive_id
feeding_date
feed_type
quantity
unit
reason
result
next_feeding_date
notes

⸻

14. HONEY HARVEST

Каждая откачка должна быть отдельной записью.

Поля:

id
hive_id
harvest_date
harvest_number
honey_type
frames_count
weight_kg
price_per_kg
total_value
notes

Автоматически рассчитывать:

total_value = weight_kg × price_per_kg

Показывать:

* мёд за месяц;
* мёд за сезон;
* мёд за год;
* мёд за всё время;
* средний сбор на улей;
* самый продуктивный улей.

⸻

15. OTHER PRODUCTS

Учитывать:

* воск;
* прополис;
* пергу;
* пыльцу;
* маточное молочко;
* маток;
* пчелиные семьи;
* пчелопакеты.

⸻

16. SWARMING

Поля:

id
hive_id
swarm_date
swarm_count
captured
new_hive_id
new_queen_id
actions
notes

⸻

17. SPLIT / MERGE

Система должна поддерживать:

Split

Hive 10
↓
Hive 10
+
Hive 35

История должна сохранять связь.

Merge

Hive 15
+
Hive 18
↓
Hive 40

Не удалять старые ульи физически из БД.

Помечать их соответствующим статусом.

⸻

18. HIVE MOVEMENTS

Улей может перемещаться между пасеками.

Сохранять:

hive_id
from_apiary_id
to_apiary_id
movement_date
reason
performed_by
notes

⸻

19. WINTERING

Создать отдельный модуль зимовки.

Поля:

hive_id
season
pre_winter_strength
food_quantity
frames_count
queen_condition
pre_winter_treatment
winter_location
start_date
end_date
spring_condition
result
notes

⸻

20. FINANCE

Расходы:

expenses

Категории:

* ульи;
* рамки;
* вощина;
* корм;
* лекарства;
* оборудование;
* транспорт;
* топливо;
* матки;
* семьи;
* ремонт;
* другое.

Доходы:

sales

Категории:

* мёд;
* воск;
* прополис;
* перга;
* пыльца;
* матки;
* семьи;
* пчелопакеты;
* другое.

Автоматически рассчитывать:

income
expenses
profit

⸻

21. DASHBOARD

Главная страница Mini App.

Показывать:

🐝 Всего ульев
👑 Матки
💪 Сильные семьи
⚠️ Слабые семьи
🩺 Больные
❗ Без матки
🔍 Требуют осмотра
🍯 Мёд за год
💰 Доход
💸 Расход
📈 Прибыль

Добавить графики:

* мёд по месяцам;
* мёд по ульям;
* сила семей;
* болезни;
* расходы;
* доходы;
* возраст маток.

⸻

22. QR SYSTEM

КРИТИЧЕСКИ ВАЖНО.

Каждый улей автоматически получает QR.

Например:

Hive UUID:
550e8400-e29b-41d4-a716-446655440000

QR ведёт на Mini App:

https://t.me/YOUR_BOT/YOUR_APP?startapp=hive_550e8400-e29b-41d4-a716-446655440000

Использовать Telegram Mini App deep linking.

После открытия:

startapp
↓
hive UUID
↓
GET /api/hives/{uuid}
↓
карточка улья

QR должен оставаться постоянным независимо от:

* смены матки;
* смены номера;
* изменения силы;
* болезни;
* перемещения;
* смены семьи.

⸻

23. QR SCANNER

В Mini App должна быть отдельная кнопка:

📷 Сканировать улей

Открывать камеру смартфона.

После сканирования QR:

QR
↓
Hive ID
↓
Hive Details

Если QR неизвестен:

❌ Улей не найден

Предложить администратору зарегистрировать его.

⸻

24. HIVE DETAILS

Это главная страница конкретного улья.

Пример:

🐝 УЛЕЙ №27
🟢 Здоров
💪 Сильная семья
Пасека:
Пасека №1
Матка:
👑 M-105
Рождение:
2024
Возраст:
2 года
Порода:
Карника
Рамки:
10
Расплод:
6
Мёд:
4
Перга:
2
🍯 Мёд 2026:
45 кг
🔍 Последний осмотр:
05.10.2026
📅 Следующий осмотр:
12.10.2026

Кнопки:

➕ Осмотр
🍯 Мёд
👑 Матка
🩺 Болезнь
💊 Лечение
🥣 Подкормка
📷 Фото
📝 Заметка
📜 История

⸻

25. HIVE TIMELINE

В каждой карточке улья сделать Timeline.

Например:

05.10.2026
🔍 Осмотр
Сила: сильная
Рамки: 10
20.09.2026
💊 Обработка
Варроатоз
15.09.2026
🍯 Откачка
8 кг
01.08.2026
🍯 Откачка
25 кг
15.05.2026
🍯 Откачка
12 кг
10.04.2026
👑 Замена матки
M-105

⸻

26. YEARLY REPORT

Создать страницу:

📊 Годовой отчёт

Пользователь выбирает:

2026

Система формирует:

Ульи

* начало года;
* конец года;
* новые;
* потерянные;
* проданные;
* объединённые;
* разделённые.

Матки

* количество;
* новые;
* заменённые;
* средний возраст;
* лучшие семьи по производительности.

Мёд

* общий сбор;
* средний сбор;
* лучший улей;
* худший улей;
* сбор по месяцам.

Болезни

* количество случаев;
* виды болезней;
* лечение;
* результат.

Финансы

Доход
Расход
Прибыль

Добавить экспорт:

PDF
Excel
CSV

⸻

27. NOTIFICATIONS

Telegram Bot должен отправлять уведомления:

🔍 Напоминание
Улей №27 давно не осматривался.
Последний осмотр:
05.10.2026

Другие уведомления:

* осмотр;
* лечение;
* обработка;
* подкормка;
* замена матки;
* зимовка;
* другие задачи.

⸻

28. PHOTOS

Можно добавлять фотографии к:

* улью;
* матке;
* осмотру;
* болезни;
* лечению;
* мёду.

Хранить:

photo_id
entity_type
entity_id
file_path
caption
uploaded_by
created_at

⸻

29. SEARCH

Глобальный поиск.

Искать:

* номер улья;
* UUID;
* матку;
* болезнь;
* пасеку.

Фильтры:

* сильные;
* слабые;
* больные;
* без матки;
* требуют осмотра;
* старые матки;
* высокая продуктивность.

⸻

30. MOBILE UX

Mini App должен быть mobile-first.

Не делать сложные таблицы на маленьком экране.

Использовать:

* карточки;
* bottom navigation;
* большие кнопки;
* понятные иконки;
* минимум текста;
* быстрые действия.

Основная навигация:

🏠 Главная
🐝 Ульи
📷 Сканер
👑 Матки
📊 Отчёты
☰ Ещё

⸻

31. OFFLINE

По возможности реализовать PWA/offline support.

Если интернет пропал:

* ранее загруженная информация доступна;
* осмотр можно сохранить локально;
* фото сохраняются локально;
* после восстановления интернета данные синхронизируются.

Для конфликтов использовать:

updated_at
version

⸻

32. SECURITY

Обязательно:

* HTTPS;
* JWT/session authentication;
* Telegram initData validation;
* RBAC;
* CORS;
* rate limiting;
* input validation;
* SQL injection protection;
* XSS protection;
* audit log.

Не хранить токены в Git.

Все секреты через .env.

Создать:

.env.example

⸻

33. DOCKER

Создать Docker Compose:

frontend
backend
postgres
bot
nginx

Для production использовать:

HTTPS
Nginx
PostgreSQL
FastAPI
Telegram Bot

⸻

34. API

Создать API endpoints.

Пример:

POST /api/auth/telegram
GET /api/dashboard
GET /api/apiaries
POST /api/apiaries
GET /api/hives
POST /api/hives
GET /api/hives/{id}
PUT /api/hives/{id}
GET /api/hives/{id}/timeline
GET /api/hives/{id}/inspections
POST /api/hives/{id}/inspections
GET /api/hives/{id}/honey
POST /api/hives/{id}/honey
GET /api/hives/{id}/diseases
POST /api/hives/{id}/diseases
GET /api/hives/{id}/treatments
POST /api/hives/{id}/treatments
GET /api/queens
POST /api/queens
GET /api/reports/yearly/{year}
GET /api/hives/{id}/qr
POST /api/hives/{id}/qr

API должно иметь правильную авторизацию для каждого endpoint.

⸻

35. VALIDATION

Нельзя сохранять:

* отрицательный вес мёда;
* отрицательное количество рамок;
* неправильную дату рождения;
* две активные матки в одном улье, если модель предполагает одну основную матку;
* отрицательные финансовые значения;
* несуществующий улей.

Все ошибки должны отображаться пользователю понятным языком.

⸻

36. AUDIT LOG

Каждое изменение важных данных:

user
date
entity
entity_id
action
old_value
new_value

Пример:

06.10.2026
User: beekeeper
Hive: #27
Матка:
M-105 → M-205

⸻

37. SEED DATA

Создать seed script.

Добавить:

* тестового пользователя;
* 2 пасеки;
* 10 ульев;
* несколько маток;
* несколько осмотров;
* заболевания;
* обработки;
* сборы мёда;
* расходы;
* продажи.

Это необходимо для демонстрации интерфейса.

⸻

38. TESTING

Создать:

Backend:

* unit tests;
* API tests;
* authentication tests.

Frontend:

* основные component tests.

Обязательно протестировать:

1. Создание улья.
2. Создание матки.
3. Привязку матки к улью.
4. Создание осмотра.
5. Добавление мёда.
6. Расчёт годового мёда.
7. QR-код.
8. Открытие улья через Telegram deep link.
9. Авторизацию Telegram.
10. Годовой отчёт.

⸻

39. НЕ ДЕЛАТЬ

Не использовать:

* SQLite для production;
* хранение всей системы в одном JSON;
* hardcoded пользователей;
* hardcoded ульи;
* hardcoded QR;
* секреты в коде;
* удаление исторических данных;
* доверие к Telegram user ID без проверки initData.

⸻

40. ПОРЯДОК РАЗРАБОТКИ

Не пытайся создать всё одним огромным файлом.

Работай по этапам.

Этап 1

Создать:

* project structure;
* Docker;
* PostgreSQL;
* FastAPI;
* React;
* Telegram authentication.

Этап 2

Создать:

* users;
* apiaries;
* hives;
* bee families;
* queens.

Этап 3

Создать:

* inspections;
* health;
* diseases;
* treatments;
* feedings.

Этап 4

Создать:

* honey;
* products;
* swarming;
* split;
* merge;
* movements;
* wintering.

Этап 5

Создать:

* QR;
* QR scanner;
* Telegram deep linking.

Этап 6

Создать:

* dashboard;
* statistics;
* yearly reports.

Этап 7

Создать:

* expenses;
* sales;
* profit.

Этап 8

Создать:

* Telegram notifications;
* reminders.

Этап 9

Создать:

* photo management;
* audit log;
* permissions.

Этап 10

Testing → security → optimization → production deployment.

⸻

41. ВАЖНО ДЛЯ CLAUDE CODE

Перед написанием большого количества кода:

1. Изучи существующий проект.
2. Если проект пустой — создай структуру.
3. Не удаляй существующий рабочий код без необходимости.
4. Создавай небольшие логические изменения.
5. После каждого этапа запускай тесты.
6. Исправляй ошибки сразу.
7. Не оставляй TODO вместо работающего функционала.
8. Не создавай mock-функции там, где требуется реальная логика.
9. Используй миграции Alembic.
10. Не меняй архитектуру без необходимости.

После каждого этапа сообщай:

Что сделано
Какие файлы изменены
Как проверить
Какие тесты прошли

⸻

42. DEFINITION OF DONE

Проект считается готовым только если:

* Telegram Mini App запускается внутри Telegram;
* пользователь авторизуется через Telegram;
* можно создать пасеку;
* можно создать улей;
* каждому улью создаётся QR;
* QR можно распечатать;
* QR можно отсканировать телефоном;
* после сканирования открывается правильный улей;
* можно посмотреть всю историю улья;
* можно создать матку;
* можно привязать матку к улью;
* автоматически рассчитывается возраст матки;
* можно проводить осмотр;
* можно записывать болезни;
* можно записывать лечение;
* можно записывать подкормки;
* можно записывать сбор мёда;
* автоматически считается мёд за год;
* можно видеть статистику;
* можно вести расходы;
* можно вести продажи;
* автоматически считается прибыль;
* можно сформировать годовой отчёт;
* работают роли пользователей;
* работает Telegram notification;
* данные хранятся в PostgreSQL;
* есть Alembic migrations;
* есть Docker;
* есть tests;
* нет секретов в Git.

⸻

ГЛАВНАЯ ЦЕЛЬ

Сделать систему, которой пчеловод реально сможет пользоваться каждый день непосредственно на пасеке.

Основной сценарий:

Пчеловод подходит к улью → открывает Telegram → нажимает «Сканировать» → сканирует QR → получает цифровой паспорт улья → проводит осмотр → добавляет данные и фотографию → сохраняет.

В конце сезона:

Отчёты → 2026 → полный анализ пасеки.

Система должна отвечать на главный вопрос:

«Что происходило с каждым ульем, семьёй и маткой за весь год, сколько мёда они дали, какие проблемы были и какой результат получен?»

Начинай разработку с анализа проекта и создания архитектуры. Затем реализуй Этап 1 и только после успешной проверки переходи к следующему этапу.