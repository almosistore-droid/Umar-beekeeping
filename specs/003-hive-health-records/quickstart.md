# Quickstart — verify stage 3

1. `docker compose -f docker-compose.dev.yml up -d --build` and load demo data
   (`... exec backend python -m app.utils.seed --telegram-id <id>`); demo data now includes
   inspections, a varroosis case, treatments with a pending reminder and feedings.
2. Open a hive → «Осмотр»: set strength, frames, queen seen → «Сохранить осмотр».
   The card shows today as last inspection, the next one in 7 days, the new strength.
3. Save an inspection with «Матка не найдена» and «Яиц нет» → warning about a possibly queenless hive.
4. «Болезнь» → Варроатоз, «Подтверждено» → hive badge «Болеет». «Лечение» linked to the case with
   next date → case «Лечение», a reminder appears on the card and on the home screen.
5. «Подкормка» → 2 л сахарного сиропа → appears in «Хронология».
6. Resolve the case → hive returns to «Активный».
7. Automated: `cd backend && pytest tests/test_health.py`, `cd frontend && npm test`.
