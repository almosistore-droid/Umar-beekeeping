#!/usr/bin/env bash
# Server protection for the beekeeping apps (Ubuntu). Run once as root, safe to run again.
#
#   ./deploy/harden.sh                  firewall (SSH, 80, 443), fail2ban for SSH, automatic security updates
#   ./deploy/harden.sh --ssh-keys-only  also forbid SSH passwords — only when a key is already installed
#   DRY_RUN=1 ./deploy/harden.sh        show what would be done
set -euo pipefail

ETC=${HARDEN_ETC:-/etc}          # tests point this to a temporary folder
KEYS=${HARDEN_KEYS:-/root/.ssh/authorized_keys}
KEYS_ONLY=0
[[ "${1:-}" == "--ssh-keys-only" ]] && KEYS_ONLY=1

say() { echo "==> $*"; }
run() { if [[ "${DRY_RUN:-0}" == 1 ]]; then echo "[dry-run] $*"; else "$@"; fi; }
put() { # put FILE CONTENT
  if [[ "${DRY_RUN:-0}" == 1 ]]; then echo "[dry-run] write $1"; else mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" > "$1"; fi
}

if [[ "${DRY_RUN:-0}" != 1 && $(id -u) -ne 0 ]]; then echo "Запустите от root: sudo ./deploy/harden.sh" >&2; exit 1; fi

SSH_PORT=$( (sshd -T 2>/dev/null || true) | awk '/^port /{print $2; exit}')
SSH_PORT=${SSH_PORT:-22}

say "Пакеты: ufw, fail2ban, unattended-upgrades"
run env DEBIAN_FRONTEND=noninteractive apt-get install -y ufw fail2ban unattended-upgrades

say "Файрвол: открыты только SSH ($SSH_PORT), 80 и 443"
run ufw default deny incoming
run ufw default allow outgoing
run ufw allow "$SSH_PORT/tcp"
run ufw allow 80/tcp
run ufw allow 443/tcp
run ufw --force enable

say "fail2ban: 5 неудачных входов по SSH → бан на час"
put "$ETC/fail2ban/jail.d/bee-sshd.local" "[sshd]
enabled = true
port = $SSH_PORT
maxretry = 5
findtime = 10m
bantime = 1h"
run systemctl enable --now fail2ban
run systemctl restart fail2ban

say "Автоматические обновления безопасности Ubuntu"
put "$ETC/apt/apt.conf.d/20auto-upgrades" 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";'

if [[ $KEYS_ONLY == 1 ]]; then
  if [[ -s "$KEYS" ]]; then
    say "SSH: вход только по ключу (пароли запрещены)"
    put "$ETC/ssh/sshd_config.d/90-bee.conf" "PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password"
    run sshd -t
    run systemctl reload ssh
  else
    say "SSH-ключ не найден в $KEYS — пароли НЕ отключаю (иначе вы потеряете доступ к серверу)"
  fi
fi

say "Готово. Проверка: ufw status · fail2ban-client status sshd"
