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
# Let's Encrypt webroot, mounted into the edge nginx (BEE_WEBROOT only for the tests)
WEBROOT=${BEE_WEBROOT:-/var/www/certbot}

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
  mkdir -p "$WEBROOT" "$EDGE/sites" "$CERTS"
  docker compose -f "$EDGE/docker-compose.yml" up -d
}

edge_reload() {
  docker exec bee-edge nginx -t && docker exec bee-edge nginx -s reload
}

CERTS="${BEE_CERTS:-/etc/bee-certs}"       # own certificates (e.g. Cloudflare Origin), win over Let's Encrypt
LETSENCRYPT="${BEE_LETSENCRYPT:-/etc/letsencrypt}"

own_cert() { [[ -f "$CERTS/$1/fullchain.pem" && -f "$CERTS/$1/privkey.pem" ]]; }

cert_file() { # cert_file DOMAIN → certificate path on the host
  if own_cert "$1"; then echo "$CERTS/$1/fullchain.pem"; else echo "$LETSENCRYPT/live/$1/fullchain.pem"; fi
}

write_site() { # write_site SLUG DOMAIN TEMPLATE — paths inside the edge container
  local cert="/etc/letsencrypt/live/$2/fullchain.pem" key="/etc/letsencrypt/live/$2/privkey.pem"
  if own_cert "$2"; then cert="/etc/bee-certs/$2/fullchain.pem"; key="/etc/bee-certs/$2/privkey.pem"; fi
  local file="$EDGE/sites/$1.conf"
  sed -e "s/__SLUG__/$1/g" -e "s/__DOMAIN__/$2/g" -e "s#__CERT__#$cert#g" -e "s#__KEY__#$key#g" "$EDGE/$3" > "$file"
}

ensure_certificate() { # ensure_certificate SLUG DOMAIN
  local slug=$1 domain=$2
  if own_cert "$domain" || [[ -f "$LETSENCRYPT/live/$domain/fullchain.pem" ]]; then return; fi
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
  local rev; rev=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)
  for part in backend frontend bot; do
    # the version in use stays as «previous»: ./deploy/client.sh rollback brings it back
    docker image inspect "beekeeping-$part:latest" >/dev/null 2>&1 && docker tag "beekeeping-$part:latest" "beekeeping-$part:previous"
    # Docker Hub is sometimes slow from the server: try again before giving up
    local try ok=0
    for try in 1 2 3; do
      if docker build -t "beekeeping-$part:latest" -t "beekeeping-$part:$rev" "$part"; then ok=1; break; fi
      [[ $try -lt 3 ]] && { echo "   сеть не ответила, попытка $((try + 1)) из 3 через 20 с…"; sleep "${BEE_RETRY_SLEEP:-20}"; }
    done
    [[ $ok == 1 ]] || die "сборка $part не удалась (нет связи с Docker Hub?) — работающая версия не тронута, повторите позже"
  done
  say "Версия $rev собрана"
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
      -e "s/__PGPASS__/$(secret 16)/" -e "s/__JWT__/$(secret 32)/" -e "s/__OWNER__/$(secret 32)/" \
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
  say "Копии баз перед обновлением"
  cmd_backup "$target" || die "копия не сделана — обновление остановлено (данные не тронуты)"
  for s in $slugs; do
    say "Обновление $s"
    compose "$s" up -d --force-recreate --remove-orphans
  done
  [[ "$target" == all ]] && cmd_sites || true
  docker image prune -f >/dev/null || true
}

current_until() { # current_until SLUG ENV → paid-until date the running backend uses ("" = no limit)
  local out; out=$(compose "$1" exec -T backend python -m app.utils.subscription show 2>/dev/null | tail -n1 | tr -d '\r' || true)
  if [[ "$out" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then echo "$out"
  elif [[ "$out" == none ]]; then echo ""
  else env_get "$2" SUBSCRIPTION_UNTIL; fi
}

set_until() { # set_until SLUG ENV DATE|none — in the client's database (wins over the .env) and in the .env
  local slug=$1 env=$2 value=$3
  env_set "$env" SUBSCRIPTION_UNTIL "$([[ $value == none ]] && echo "" || echo "$value")"
  compose "$slug" up -d backend
  compose "$slug" exec -T backend python -m app.utils.subscription set "$value"
}

cmd_extend() {
  local slug=${1:-} when=${2:-}
  local env; env=$(client_env "$slug")
  [[ -n "$when" ]] || die "укажите дату (2027-10-17), срок (+1year, +6months, +30days) или none (без срока)"
  local new
  if [[ "$when" == none ]]; then
    new=none
  elif [[ "$when" == +* ]]; then
    # from the current end date, or from today if it has already passed
    local cur; cur=$(current_until "$slug" "$env")
    local base; base=$(date +%F)
    [[ -n "$cur" && "$cur" > "$base" ]] && base=$cur
    new=$(date -d "$base ${when#+}" +%F) || die "непонятный срок «$when»"
  else
    new=$(date -d "$when" +%F) || die "непонятная дата «$when»"
  fi
  set_until "$slug" "$env" "$new"
  say "$slug: подписка $([[ $new == none ]] && echo "без срока" || echo "до $new")"
}

cmd_block() {
  local slug=${1:-}
  local env; env=$(client_env "$slug")
  set_until "$slug" "$env" "$(date -d yesterday +%F)"
  say "$slug: доступ закрыт (данные сохранены). Открыть: ./deploy/client.sh extend $slug +1month"
}

cmd_list() {
  local today; today=$(date +%F)
  printf "%-12s %-24s %-20s %-12s %s\n" "КЛИЕНТ" "ДОМЕН" "НАЗВАНИЕ" "ДО" "СОСТОЯНИЕ"
  for s in $(all_slugs); do
    local env="$CLIENTS/$s.env"
    local until; until=$(current_until "$s" "$env")
    local paid="оплачено"
    if [[ -n "$until" && "$today" > "$until" ]]; then paid="ЗАКРЫТО"
    elif [[ -n "$until" && "$(date -d "$until -7 days" +%F)" < "$today" ]]; then paid="скоро конец"; fi
    local running; running=$(compose "$s" ps --status running -q 2>/dev/null | wc -l || true)
    printf "%-12s %-24s %-20s %-12s %s, контейнеров: %s\n" "$s" "$(env_get "$env" DOMAIN)" \
      "$(env_get "$env" BRAND_NAME)" "${until:-без срока}" "$paid" "$running"
  done
}

BACKUP_ENV="$ROOT/deploy/backup.env"
MAX_TELEGRAM_BYTES=$((49 * 1024 * 1024))

backup_get() { [[ -f "$BACKUP_ENV" ]] && env_get "$BACKUP_ENV" "$1" || true; }

telegram_send() { # telegram_send FILE CAPTION — to the owner's chat with the backup bot; 0 = delivered
  local token chat; token=$(backup_get BACKUP_BOT_TOKEN); chat=$(backup_get BACKUP_CHAT_ID)
  [[ -n "$token" && -n "$chat" ]] || { echo "   (копии в Telegram не настроены: ./deploy/client.sh backup-setup)"; return 1; }
  local out
  out=$(curl -sS --max-time 300 -F "chat_id=$chat" -F "caption=$2" -F "document=@$1" \
    "https://api.telegram.org/bot$token/sendDocument" 2>&1) || true
  [[ "$out" == *'"ok":true'* ]]
}

telegram_text() { # telegram_text MESSAGE — short message to the owner (alerts)
  local token chat; token=$(backup_get BACKUP_BOT_TOKEN); chat=$(backup_get BACKUP_CHAT_ID)
  [[ -n "$token" && -n "$chat" ]] || return 1
  local out
  out=$(curl -sS --max-time 30 --data-urlencode "chat_id=$chat" --data-urlencode "text=$1" \
    "https://api.telegram.org/bot$token/sendMessage" 2>&1) || true
  [[ "$out" == *'"ok":true'* ]]
}

encrypt_file() { # encrypt_file IN OUT — AES-256 with BACKUP_PASSWORD (never on the command line)
  BACKUP_PASSWORD=$(backup_get BACKUP_PASSWORD) \
    openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:BACKUP_PASSWORD -in "$1" -out "$2"
}

cmd_backup() { # backup [SLUG|all] [--send]
  local target=all send=0
  for arg in "$@"; do [[ "$arg" == --send ]] && send=1 || target=$arg; done
  local slugs; if [[ "$target" == all ]]; then slugs=$(all_slugs); else slugs=$target; fi
  mkdir -p "$BACKUPS"; chmod 700 "$BACKUPS"
  local failed=0
  for s in $slugs; do
    local env; env=$(client_env "$s")
    local file; file="$BACKUPS/$s-$(date +%F-%H%M).sql.gz"
    if ! compose "$s" exec -T postgres pg_dump --no-owner -U "$(env_get "$env" POSTGRES_USER)" "$(env_get "$env" POSTGRES_DB)" \
        | gzip > "$file.part" || [[ ! -s "$file.part" ]]; then
      rm -f "$file.part"; echo "Ошибка: копия $s не сделана" >&2; failed=1; continue
    fi
    mv "$file.part" "$file"; chmod 600 "$file"
    say "$s → $file ($(du -h "$file" | cut -f1))"
    if [[ $send == 1 ]]; then
      encrypt_file "$file" "$file.enc"
      if (( $(stat -c %s "$file.enc") > MAX_TELEGRAM_BYTES )); then
        echo "   больше 49 МБ — в Telegram не помещается, осталась на сервере" >&2; failed=1
      elif telegram_send "$file.enc" "Копия базы $s · $(date '+%d.%m.%Y %H:%M') · зашифрована"; then
        say "   отправлена в Telegram"
      else
        echo "   не удалось отправить в Telegram" >&2; failed=1
      fi
      rm -f "$file.enc"
    fi
  done
  # keep 30 days
  find "$BACKUPS" -name '*.sql.gz' -mtime +30 -delete
  return $failed
}

cmd_rollback() { # back to the version before the last build
  for part in backend frontend bot; do
    docker image inspect "beekeeping-$part:previous" >/dev/null 2>&1 || die "предыдущей версии нет (сборка была одна)"
  done
  for part in backend frontend bot; do docker tag "beekeeping-$part:previous" "beekeeping-$part:latest"; done
  say "Возвращена предыдущая версия; перезапуск клиентов"
  echo "   Если новая версия уже изменила базу, восстановите копию до обновления: ./deploy/client.sh restore ИМЯ backups/…"
  local s; for s in $(all_slugs); do compose "$s" up -d --force-recreate --remove-orphans; done
}

cmd_backup_setup() {
  [[ -f "$BACKUP_ENV" ]] && say "Настройки уже есть — перезаписываю (старые копии откроются старым паролем)"
  local token chat
  read -rsp "Токен бота для копий (из @BotFather; можно бота любого клиента): " token; echo
  read -rp "Ваш Telegram ID (узнать: @userinfobot): " chat
  [[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]] || die "это не похоже на токен бота"
  [[ "$chat" =~ ^-?[0-9]+$ ]] || die "Telegram ID — это число"
  local pass; pass=$(secret 16)
  ( umask 077; printf 'BACKUP_BOT_TOKEN=%s\nBACKUP_CHAT_ID=%s\nBACKUP_PASSWORD=%s\n' "$token" "$chat" "$pass" > "$BACKUP_ENV" )
  if telegram_text "Копии баз будут приходить сюда каждую ночь. Пароль для расшифровки храните отдельно от телефона."; then
    say "Проверочное сообщение отправлено — откройте чат с ботом"
  else
    echo "Не получилось написать вам: откройте этого бота в Telegram, нажмите «Start» и повторите." >&2
  fi
  say "ПАРОЛЬ КОПИЙ: $pass"
  echo "   Запишите его в надёжное место (не в чат, не на этот сервер). Без него копию не открыть."
}

cmd_decrypt() { # decrypt FILE.sql.gz.enc → FILE.sql.gz (asks for the password if backup.env is not here)
  local in=${1:-}
  [[ -f "$in" && "$in" == *.enc ]] || die "укажите файл .enc"
  local pass; pass=$(backup_get BACKUP_PASSWORD)
  [[ -n "$pass" ]] || { read -rsp "Пароль копий: " pass; echo; }
  BACKUP_PASSWORD=$pass openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_PASSWORD -in "$in" -out "${in%.enc}" \
    || die "не расшифровалось: неверный пароль или файл повреждён"
  say "Готово: ${in%.enc}"
}

cmd_restore() { # restore SLUG FILE(.sql.gz|.sql.gz.enc)
  local slug=${1:-} file=${2:-}
  local env; env=$(client_env "$slug")
  [[ -f "$file" ]] || die "нет файла $file"
  if [[ "$file" == *.enc ]]; then cmd_decrypt "$file"; file=${file%.enc}; fi
  gzip -t "$file" 2>/dev/null || die "файл повреждён (не gzip)"
  if [[ "${BEE_YES:-}" != 1 ]]; then
    echo "ВНИМАНИЕ: все данные «$slug» будут заменены копией $file."
    local answer; read -rp "Для подтверждения введите имя клиента ($slug): " answer
    [[ "$answer" == "$slug" ]] || die "отменено"
  fi
  say "Сначала копия текущего состояния (на всякий случай)"
  cmd_backup "$slug" || die "не удалось сделать копию текущих данных — восстановление остановлено"
  local user db; user=$(env_get "$env" POSTGRES_USER); db=$(env_get "$env" POSTGRES_DB)
  compose "$slug" stop backend bot >/dev/null 2>&1 || true
  compose "$slug" exec -T postgres psql -q -v ON_ERROR_STOP=1 -U "$user" -d "$db" \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION \"$user\";"
  gunzip -c "$file" | compose "$slug" exec -T postgres psql -q -v ON_ERROR_STOP=1 -U "$user" -d "$db" >/dev/null
  compose "$slug" up -d
  say "$slug восстановлен из $(basename "$file")"
}

# ---------- health check and alerts ----------

check_client() { # prints problems of one client, one per line
  local s=$1 env="$CLIENTS/$1.env"
  local domain; domain=$(env_get "$env" DOMAIN)
  local health
  health=$(compose "$s" exec -T backend python -c \
    "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=5).status)" 2>/dev/null \
    | tail -n1 | tr -d '\r' || true)
  [[ "$health" == 200 ]] || echo "$s: приложение не отвечает"
  local pem; pem=$(cert_file "$domain")
  if [[ -f "$pem" ]]; then
    local end; end=$(openssl x509 -enddate -noout -in "$pem" | cut -d= -f2)
    local days=$(( ( $(date -d "$end" +%s) - $(date +%s) ) / 86400 ))
    (( days < 14 )) && echo "$s: сертификат $domain истекает через $days дн."
  fi
  return 0
}

cmd_check() { # check [--alert]: problems on screen; with --alert also to the owner's Telegram (once per 6 h)
  local alert=0; [[ "${1:-}" == --alert ]] && alert=1
  local problems=""
  for s in $(all_slugs); do problems+=$(check_client "$s"); problems+=$'\n'; done
  local used; used=$(df --output=pcent "${BEE_DISK:-/}" | tail -n1 | tr -dc '0-9')
  (( used >= 85 )) && problems+="Диск сервера заполнен на ${used}%"$'\n'
  problems=$(printf '%s' "$problems" | sed '/^$/d')
  if [[ -z "$problems" ]]; then
    say "Всё в порядке: клиентов $(all_slugs | wc -w), диск ${used}%"
    rm -f "$BACKUPS/.alert"
    return 0
  fi
  echo "$problems"
  if [[ $alert == 1 ]]; then
    mkdir -p "$BACKUPS"
    local stamp="$BACKUPS/.alert" sum; sum=$(printf '%s' "$problems" | sha1sum | cut -c1-12)
    if [[ ! -f "$stamp" || "$(cut -d' ' -f1 "$stamp")" != "$sum" || $(( $(date +%s) - $(cut -d' ' -f2 "$stamp") )) -gt 21600 ]]; then
      telegram_text "⚠️ Сервер пасек: $problems" && echo "$sum $(date +%s)" > "$stamp"
    fi
  fi
  return 1
}

cmd_cron() { # nightly copies to Telegram, certificates, checks every 15 min
  local file=${BEE_CRON_FILE:-/etc/cron.d/beekeeping}
  cat > "$file" <<CRON
# made by deploy/client.sh cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 2 * * * root $ROOT/deploy/client.sh backup all --send >> /var/log/beekeeping-backup.log 2>&1
0 3 * * * root $ROOT/deploy/client.sh renew >> /var/log/beekeeping-renew.log 2>&1
*/15 * * * * root $ROOT/deploy/client.sh check --alert > /dev/null 2>&1
CRON
  chmod 644 "$file"
  rm -f /etc/cron.d/certbot-bee /etc/cron.d/backup-bee 2>/dev/null || true
  say "Расписание записано в $file: копии 02:30, сертификаты 03:00, проверка каждые 15 минут"
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
  [[ -n "$(env_get "$env" OWNER_TOKEN)" ]] || env_set "$env" OWNER_TOKEN "$(secret 32)"
  say "Остановка старой установки (данные остаются)"
  (cd "$ROOT" && docker compose -f docker-compose.yml down)
  cmd_start "$slug"
  mv "$old" "$old.moved"
  say "Перенесено. Старый .env переименован в .env.moved; настройки клиента теперь в $env"
}

# ---------- certificates and sites ----------

cmd_sites() { # rewrite every site from the templates (after an update or a certificate change)
  local s; for s in $(all_slugs); do
    local d; d=$(env_get "$CLIENTS/$s.env" DOMAIN)
    [[ -n "$d" && -f "$(cert_file "$d")" ]] && write_site "$s" "$d" site.conf.template
  done
  if [[ -f "$ROOT/deploy/owner.env" ]]; then
    local od; od=$(env_get "$ROOT/deploy/owner.env" DOMAIN)
    [[ -n "$od" && -f "$(cert_file "$od")" ]] && write_site _owner "$od" owner-site.conf.template
  fi
  edge_up >/dev/null
  edge_reload
}

cmd_cert_files() { # cert-files CERT.pem KEY.pem — own certificate (Cloudflare Origin, purchased), no renewal by us
  local cert=${1:-} key=${2:-}
  [[ -f "$cert" && -f "$key" ]] || die "укажите файлы сертификата и ключа: cert-files cert.pem key.pem"
  openssl x509 -noout -in "$cert" 2>/dev/null || die "$cert — не сертификат (нужен PEM: -----BEGIN CERTIFICATE-----)"
  local a b
  a=$(openssl x509 -noout -pubkey -in "$cert" | sha256sum); b=$(openssl pkey -pubout -in "$key" 2>/dev/null | sha256sum)
  [[ "$a" == "$b" ]] || die "ключ не подходит к сертификату"
  local domains=() s d
  for s in $(all_slugs); do domains+=("$(env_get "$CLIENTS/$s.env" DOMAIN)"); done
  [[ -f "$ROOT/deploy/owner.env" ]] && domains+=("$(env_get "$ROOT/deploy/owner.env" DOMAIN)")
  local used=0
  for d in "${domains[@]}"; do
    [[ -n "$d" ]] || continue
    if openssl x509 -noout -in "$cert" -checkhost "$d" | grep -q "does match"; then
      ( umask 077; mkdir -p "$CERTS/$d"; cp "$cert" "$CERTS/$d/fullchain.pem"; cp "$key" "$CERTS/$d/privkey.pem" )
      say "$d: свой сертификат установлен (до $(openssl x509 -noout -enddate -in "$cert" | cut -d= -f2))"
      used=1
    fi
  done
  [[ $used == 1 ]] || die "сертификат не подходит ни к одному домену на этом сервере"
  cmd_sites
}

# ---------- owner panel ----------

owner_compose() {
  OWNER_ENV="$ROOT/deploy/owner.env" CLIENTS_DIR="$CLIENTS" \
    docker compose -f "$ROOT/deploy/owner.yml" --env-file "$ROOT/deploy/owner.env" "$@"
}

cmd_owner() {
  local domain=${1:-}
  [[ "$domain" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || die "укажите домен панели, например admin.fayziumar.tj"
  docker image inspect beekeeping-backend:latest >/dev/null 2>&1 || die "сначала ./deploy/client.sh build"
  local env="$ROOT/deploy/owner.env"
  if [[ ! -f "$env" ]]; then
    local pass; pass=$(secret 8)
    printf 'DOMAIN=%s\nOWNER_PASSWORD=%s\nOWNER_SECRET=%s\nTIMEZONE=Asia/Dushanbe\n' "$domain" "$pass" "$(secret 32)" > "$env"
    chmod 600 "$env"
    say "Пароль панели владельца: $pass"
    echo "   Сохраните его в надёжном месте. Новый пароль: ./deploy/client.sh owner-password"
  else
    env_set "$env" DOMAIN "$domain"
  fi
  # every client needs its own key for the panel
  for s in $(all_slugs); do
    local cenv="$CLIENTS/$s.env"
    if [[ -z "$(env_get "$cenv" OWNER_TOKEN)" ]]; then
      env_set "$cenv" OWNER_TOKEN "$(secret 32)"
      say "Ключ панели для $s добавлен"
      compose "$s" up -d --force-recreate backend
    fi
  done
  edge_up
  owner_compose up -d --force-recreate
  ensure_certificate _owner "$domain"
  write_site _owner "$domain" owner-site.conf.template
  edge_reload
  say "Панель владельца: https://$domain"
}

cmd_owner_password() {
  local env="$ROOT/deploy/owner.env"
  [[ -f "$env" ]] || die "панель ещё не установлена: ./deploy/client.sh owner ДОМЕН"
  local pass; pass=$(secret 8)
  env_set "$env" OWNER_PASSWORD "$pass"
  owner_compose up -d --force-recreate
  say "Новый пароль панели владельца: $pass"
}

cmd_renew() { # Let's Encrypt only for domains without an own certificate (those need no renewal from us)
  local dir d
  for dir in "$LETSENCRYPT"/renewal/*.conf; do
    [[ -f "$dir" ]] || continue
    d=$(basename "$dir" .conf)
    own_cert "$d" && continue
    certbot renew --cert-name "$d" --webroot -w "$WEBROOT" --quiet --deploy-hook "docker exec bee-edge nginx -s reload"
  done
}

usage() {
  cat <<'TXT'
Клиенты подписки на этом сервере (у каждого своя копия приложения):
  ./deploy/client.sh build                    собрать новую версию (после git pull)
  ./deploy/client.sh update all               перезапустить всех клиентов на новой версии
  ./deploy/client.sh add ИМЯ ДОМЕН            новый клиент (создаст clients/ИМЯ.env)
  ./deploy/client.sh logo ИМЯ файл.png        логотип клиента
  ./deploy/client.sh start ИМЯ                сертификат + сайт + запуск (и после правки .env)
  ./deploy/client.sh extend ИМЯ +1year        продлить (или +6months, +30days, 2027-10-17, none — без срока)
  ./deploy/client.sh block ИМЯ                закрыть доступ сейчас (данные сохраняются)
  ./deploy/client.sh list                     все клиенты, домены, срок оплаты
  ./deploy/client.sh backup all [--send]      копии баз в backups/ (30 дней); --send — зашифрованные вам в Telegram
  ./deploy/client.sh backup-setup             куда присылать копии (бот и ваш Telegram ID), пароль копий
  ./deploy/client.sh restore ИМЯ файл         вернуть базу клиента из копии (.sql.gz или .sql.gz.enc)
  ./deploy/client.sh decrypt файл.enc         расшифровать копию из Telegram
  ./deploy/client.sh check [--alert]          всё ли работает (приложения, сертификаты, диск)
  ./deploy/client.sh cron                     расписание: копии ночью, сертификаты, проверка каждые 15 минут
  ./deploy/client.sh rollback                 вернуть предыдущую версию после неудачного обновления
  ./deploy/client.sh logs ИМЯ [backend|bot]   журнал
  ./deploy/client.sh stop ИМЯ                 остановить (данные сохраняются)
  ./deploy/client.sh adopt ИМЯ                перенести старую установку (.env) в клиенты
  ./deploy/client.sh renew                    продлить сертификаты (для cron)
  ./deploy/client.sh owner ДОМЕН              панель владельца: все клиенты, продление одной кнопкой
  ./deploy/client.sh owner-password           новый пароль панели владельца
  ./deploy/client.sh cert-files cert.pem key.pem  свой сертификат (Cloudflare Origin) вместо Let's Encrypt
  ./deploy/client.sh sites                    пересоздать настройки сайтов (после обновления)
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
    backup-setup) cmd_backup_setup "$@" ;;
    restore) cmd_restore "$@" ;;
    decrypt) cmd_decrypt "$@" ;;
    check) cmd_check "$@" ;;
    cron) cmd_cron "$@" ;;
    rollback) cmd_rollback "$@" ;;
    logs) cmd_logs "$@" ;;
    stop) cmd_stop "$@" ;;
    adopt) cmd_adopt "$@" ;;
    renew) cmd_renew "$@" ;;
    owner) cmd_owner "$@" ;;
    sites) cmd_sites "$@" ;;
    cert-files) cmd_cert_files "$@" ;;
    owner-password) cmd_owner_password "$@" ;;
    *) usage ;;
  esac
}

main "$@"
