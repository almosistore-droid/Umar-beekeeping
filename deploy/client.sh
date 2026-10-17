#!/usr/bin/env bash
# Subscription clients on one server: each client is its own copy of the app
# (database, brand, domain, bot) behind one shared HTTPS nginx (deploy/edge).
#
#   ./deploy/client.sh build                 build the images once (after git pull)
#   ./deploy/client.sh add SLUG DOMAIN       new client: creates clients/SLUG.env
#   ./deploy/client.sh logo SLUG FILE.png    client's logo
#   ./deploy/client.sh start SLUG            certificate + site + start (also after editing the .env)
#   ./deploy/client.sh update [SLUG|all]     restart on the new images (after build)
#   ./deploy/client.sh extend SLUG DATE|+1year|+30days   pay period up to the date
#   ./deploy/client.sh block SLUG            close access now (data is kept)
#   ./deploy/client.sh list                  clients, domains, paid until, state
#   ./deploy/client.sh backup [SLUG|all]     database dump into backups/
#   ./deploy/client.sh logs SLUG [service]
#   ./deploy/client.sh stop SLUG             stop (data is kept)
#   ./deploy/client.sh adopt SLUG            move the old single install (.env, project «beekeeping») here
#   ./deploy/client.sh renew                 renew certificates (cron)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENTS="$ROOT/clients"
EDGE="$ROOT/deploy/edge"
BACKUPS="$ROOT/backups"
WEBROOT=/var/www/certbot

die() { echo "Ошибка: $*" >&2; exit 1; }
say() { echo "==> $*"; }

env_get() { # env_get FILE KEY
  grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2- || true
}

env_set() { # env_set FILE KEY VALUE
  local file=$1 key=$2 value=$3
  if grep -qE "^$key=" "$file"; then
    local tmp; tmp=$(mktemp)
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k {print k "=" v; next} {print}' "$file" > "$tmp"
    cat "$tmp" > "$file"; rm -f "$tmp"
  else
    echo "$key=$value" >> "$file"
  fi
}

check_slug() {
  [[ "${1:-}" =~ ^[a-z][a-z0-9]{1,19}$ ]] || die "имя клиента — латиница и цифры, 2–20 символов, с буквы (например asal)"
}

client_env() {
  check_slug "$1"
  local f="$CLIENTS/$1.env"
  [[ -f "$f" ]] || die "клиента «$1» нет (файл $f)"
  echo "$f"
}

secret() { # letters and digits only: the password goes into the database URL
  openssl rand -hex "$1"
}

compose() { # compose SLUG args…
  local slug=$1; shift
  local env; env=$(client_env "$slug")
  local project; project=$(env_get "$env" COMPOSE_PROJECT); project=${project:-bee-$slug}
  local profiles=()
  [[ -n "$(env_get "$env" TELEGRAM_BOT_TOKEN)" ]] && profiles=(--profile bot)
  mkdir -p "$CLIENTS/$slug"
  SLUG=$slug CLIENT_ENV=$env CLIENT_DIR="$CLIENTS/$slug" \
    docker compose -p "$project" -f "$ROOT/deploy/client.yml" --env-file "$env" "${profiles[@]}" "$@"
}

all_slugs() {
  shopt -s nullglob
  for f in "$CLIENTS"/*.env; do basename "$f" .env; done
}

edge_up() {
  docker network inspect bee-edge >/dev/null 2>&1 || docker network create bee-edge >/dev/null
  mkdir -p "$WEBROOT" "$EDGE/sites"
  docker compose -f "$EDGE/docker-compose.yml" up -d
}

edge_reload() {
  docker exec bee-edge nginx -t && docker exec bee-edge nginx -s reload
}

write_site() { # write_site SLUG DOMAIN TEMPLATE
  sed -e "s/__SLUG__/$1/g" -e "s/__DOMAIN__/$2/g" "$EDGE/$3" > "$EDGE/sites/$1.conf"
}

ensure_certificate() { # ensure_certificate SLUG DOMAIN
  local slug=$1 domain=$2
  if [[ -f "/etc/letsencrypt/live/$domain/fullchain.pem" ]]; then return; fi
  command -v certbot >/dev/null || die "нет certbot: apt install -y certbot"
  say "Сертификат для $domain (домен уже должен смотреть на этот сервер)"
  write_site "$slug" "$domain" site-http.conf.template
  edge_reload
  local email=${CERT_EMAIL:-}
  local mail_args=(--register-unsafely-without-email)
  [[ -n "$email" ]] && mail_args=(-m "$email")
  certbot certonly --webroot -w "$WEBROOT" -d "$domain" --agree-tos --non-interactive "${mail_args[@]}"
}

cmd_build() {
  cd "$ROOT"
  say "Сборка образов (один раз для всех клиентов)"
  docker build -t beekeeping-backend:latest backend
  docker build -t beekeeping-frontend:latest frontend
  docker build -t beekeeping-bot:latest bot
  say "Готово. Перезапустить клиентов на новой версии: ./deploy/client.sh update all"
}

cmd_add() {
  local slug=${1:-} domain=${2:-}
  check_slug "$slug"
  [[ "$domain" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || die "укажите домен, например asal.tj"
  local env="$CLIENTS/$slug.env"
  [[ -f "$env" ]] && die "клиент «$slug» уже есть: $env"
  for f in "$CLIENTS"/*.env; do
    [[ -f "$f" && "$(env_get "$f" DOMAIN)" == "$domain" ]] && die "домен $domain уже у клиента $(basename "$f" .env)"
  done
  mkdir -p "$CLIENTS/$slug"; chmod 700 "$CLIENTS"
  local until; until=$(date -d "+30 days" +%F)
  sed -e "s/__SLUG__/$slug/g" -e "s/__DOMAIN__/$domain/g" -e "s/__UNTIL__/$until/" \
      -e "s/__PGPASS__/$(secret 16)/" -e "s/__JWT__/$(secret 32)/" \
      "$ROOT/deploy/client.env.template" > "$env"
  chmod 600 "$env"
  say "Создан $env (подписка до $until)"
  echo "Дальше:"
  echo "  1) nano $env   — название, цвет, контакт, токен бота, Telegram ID администратора"
  echo "  2) ./deploy/client.sh logo $slug /путь/logo.png"
  echo "  3) DNS: запись A для $domain → IP этого сервера"
  echo "  4) ./deploy/client.sh start $slug"
}

cmd_logo() {
  local slug=${1:-} file=${2:-}
  client_env "$slug" >/dev/null
  [[ -f "$file" ]] || die "нет файла $file"
  [[ "$(head -c 8 "$file" | od -An -tx1 | tr -d ' \n')" == "89504e470d0a1a0a" ]] || die "нужен PNG-файл"
  mkdir -p "$CLIENTS/$slug"
  cp "$file" "$CLIENTS/$slug/logo.png"
  chmod 644 "$CLIENTS/$slug/logo.png"
  say "Логотип сохранён. Значки и ярлык обновятся сами (кэш по дате файла)."
}

cmd_start() {
  local slug=${1:-}
  local env; env=$(client_env "$slug")
  local domain; domain=$(env_get "$env" DOMAIN)
  [[ -n "$domain" ]] || die "в $env нет DOMAIN"
  docker image inspect beekeeping-backend:latest >/dev/null 2>&1 || die "сначала ./deploy/client.sh build"
  edge_up
  say "Запуск $slug"
  compose "$slug" up -d --remove-orphans
  ensure_certificate "$slug" "$domain"
  write_site "$slug" "$domain" site.conf.template
  edge_reload
  say "Готово: https://$domain"
  [[ -z "$(env_get "$env" TELEGRAM_BOT_TOKEN)" ]] && echo "   (без бота: TELEGRAM_BOT_TOKEN пуст — вход только по логину и паролю)"
  return 0
}

cmd_update() {
  local target=${1:-all}
  local slugs; if [[ "$target" == all ]]; then slugs=$(all_slugs); else slugs=$target; fi
  for s in $slugs; do
    say "Обновление $s"
    compose "$s" up -d --force-recreate --remove-orphans
  done
  docker image prune -f >/dev/null || true
}

cmd_extend() {
  local slug=${1:-} when=${2:-}
  local env; env=$(client_env "$slug")
  [[ -n "$when" ]] || die "укажите дату (2027-10-17) или срок (+1year, +6months, +30days)"
  local new
  if [[ "$when" == +* ]]; then
    # from the current end date, or from today if it has already passed
    local cur; cur=$(env_get "$env" SUBSCRIPTION_UNTIL)
    local base; base=$(date +%F)
    [[ -n "$cur" && "$cur" > "$base" ]] && base=$cur
    new=$(date -d "$base ${when#+}" +%F) || die "непонятный срок «$when»"
  else
    new=$(date -d "$when" +%F) || die "непонятная дата «$when»"
  fi
  env_set "$env" SUBSCRIPTION_UNTIL "$new"
  compose "$slug" up -d --force-recreate backend
  say "$slug: подписка до $new"
}

cmd_block() {
  local slug=${1:-}
  local env; env=$(client_env "$slug")
  env_set "$env" SUBSCRIPTION_UNTIL "$(date -d yesterday +%F)"
  compose "$slug" up -d --force-recreate backend
  say "$slug: доступ закрыт (данные сохранены). Открыть: ./deploy/client.sh extend $slug +1month"
}

cmd_list() {
  local today; today=$(date +%F)
  printf "%-12s %-24s %-20s %-12s %s\n" "КЛИЕНТ" "ДОМЕН" "НАЗВАНИЕ" "ДО" "СОСТОЯНИЕ"
  for s in $(all_slugs); do
    local env="$CLIENTS/$s.env"
    local until; until=$(env_get "$env" SUBSCRIPTION_UNTIL)
    local paid="оплачено"
    if [[ -n "$until" && "$today" > "$until" ]]; then paid="ЗАКРЫТО"
    elif [[ -n "$until" && "$(date -d "$until -7 days" +%F)" < "$today" ]]; then paid="скоро конец"; fi
    local running; running=$(compose "$s" ps --status running -q 2>/dev/null | wc -l || true)
    printf "%-12s %-24s %-20s %-12s %s, контейнеров: %s\n" "$s" "$(env_get "$env" DOMAIN)" \
      "$(env_get "$env" BRAND_NAME)" "${until:-без срока}" "$paid" "$running"
  done
}

cmd_backup() {
  local target=${1:-all}
  local slugs; if [[ "$target" == all ]]; then slugs=$(all_slugs); else slugs=$target; fi
  mkdir -p "$BACKUPS"; chmod 700 "$BACKUPS"
  for s in $slugs; do
    local env; env=$(client_env "$s")
    local file; file="$BACKUPS/$s-$(date +%F-%H%M).sql.gz"
    compose "$s" exec -T postgres pg_dump -U "$(env_get "$env" POSTGRES_USER)" "$(env_get "$env" POSTGRES_DB)" | gzip > "$file"
    say "$s → $file"
  done
  # keep 30 days
  find "$BACKUPS" -name '*.sql.gz' -mtime +30 -delete
}

cmd_logs() {
  local slug=${1:-}; shift || true
  compose "$slug" logs --tail 100 -f "$@"
}

cmd_stop() {
  local slug=${1:-}
  local env; env=$(client_env "$slug")
  compose "$slug" down
  rm -f "$EDGE/sites/$slug.conf"
  edge_reload || true
  say "$slug остановлен, данные сохранены. Запустить снова: ./deploy/client.sh start $slug"
}

cmd_adopt() {
  local slug=${1:-}
  check_slug "$slug"
  local old="$ROOT/.env"
  [[ -f "$old" ]] || die "нет $old — переносить нечего"
  local env="$CLIENTS/$slug.env"
  [[ -f "$env" ]] && die "клиент «$slug» уже есть"
  mkdir -p "$CLIENTS/$slug"; chmod 700 "$CLIENTS"
  cp "$old" "$env"; chmod 600 "$env"
  env_set "$env" SLUG "$slug"
  # same Docker project name → the same volumes (beekeeping_pgdata, beekeeping_uploads): data stays
  env_set "$env" COMPOSE_PROJECT beekeeping
  env_set "$env" UVICORN_WORKERS 1
  grep -qE "^BRAND_NAME=" "$env" || env_set "$env" BRAND_NAME "Fayzi Umar"
  say "Остановка старой установки (данные остаются)"
  (cd "$ROOT" && docker compose -f docker-compose.yml down)
  cmd_start "$slug"
  mv "$old" "$old.moved"
  say "Перенесено. Старый .env переименован в .env.moved; настройки клиента теперь в $env"
}

cmd_renew() {
  certbot renew --webroot -w "$WEBROOT" --quiet --deploy-hook "docker exec bee-edge nginx -s reload"
}

usage() {
  cat <<'TXT'
Клиенты подписки на этом сервере (у каждого своя копия приложения):
  ./deploy/client.sh build                    собрать новую версию (после git pull)
  ./deploy/client.sh update all               перезапустить всех клиентов на новой версии
  ./deploy/client.sh add ИМЯ ДОМЕН            новый клиент (создаст clients/ИМЯ.env)
  ./deploy/client.sh logo ИМЯ файл.png        логотип клиента
  ./deploy/client.sh start ИМЯ                сертификат + сайт + запуск (и после правки .env)
  ./deploy/client.sh extend ИМЯ +1year        продлить (или +6months, +30days, 2027-10-17)
  ./deploy/client.sh block ИМЯ                закрыть доступ сейчас (данные сохраняются)
  ./deploy/client.sh list                     все клиенты, домены, срок оплаты
  ./deploy/client.sh backup all               копии баз в backups/ (хранятся 30 дней)
  ./deploy/client.sh logs ИМЯ [backend|bot]   журнал
  ./deploy/client.sh stop ИМЯ                 остановить (данные сохраняются)
  ./deploy/client.sh adopt ИМЯ                перенести старую установку (.env) в клиенты
  ./deploy/client.sh renew                    продлить сертификаты (для cron)
TXT
}

main() {
  local cmd=${1:-help}; shift || true
  case "$cmd" in
    build) cmd_build "$@" ;;
    add) cmd_add "$@" ;;
    logo) cmd_logo "$@" ;;
    start) cmd_start "$@" ;;
    update) cmd_update "$@" ;;
    extend) cmd_extend "$@" ;;
    block) cmd_block "$@" ;;
    list) cmd_list "$@" ;;
    backup) cmd_backup "$@" ;;
    logs) cmd_logs "$@" ;;
    stop) cmd_stop "$@" ;;
    adopt) cmd_adopt "$@" ;;
    renew) cmd_renew "$@" ;;
    *) usage ;;
  esac
}

main "$@"
