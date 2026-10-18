"""Stage 10 (security): no secrets in the repository — bot tokens, private keys, real .env files."""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BOT_TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
FILLED_SECRET = re.compile(r"^(?:JWT_SECRET|POSTGRES_PASSWORD|OWNER_TOKEN|OWNER_PASSWORD|BACKUP_PASSWORD)=(\S{12,})$", re.M)
PLACEHOLDERS = {"change_me_long_random_password"}


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [REPO / f for f in out.splitlines() if f]


def test_no_env_files_are_tracked():
    names = [p.relative_to(REPO).as_posix() for p in tracked_files()]
    bad = [n for n in names if (n.endswith(".env") or "/.env" in n or n == ".env") and not n.endswith(".env.example")]
    assert not bad, f"secret files in git: {bad}"


def test_no_tokens_keys_or_filled_secrets():
    found = []
    for path in tracked_files():
        if not path.is_file() or path.suffix in {".png", ".webp", ".ttf", ".pdf", ".ico", ".jpg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(REPO).as_posix()
        if BOT_TOKEN.search(text):
            found.append(f"{rel}: Telegram bot token")
        if PRIVATE_KEY.search(text):
            found.append(f"{rel}: private key")
        for m in FILLED_SECRET.finditer(text):
            if m.group(1) not in PLACEHOLDERS and "__" not in m.group(1):
                found.append(f"{rel}: {m.group(0).split('=')[0]} has a value")
    assert not found, found
